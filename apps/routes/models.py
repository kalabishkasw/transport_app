from django.db import models


class Route(models.Model):
    """
    Маршрут пасажирського перевезення (наприклад, «Ужгород Прага»).
    Описує географію: кінцеві пункти, дистанцію, тривалість.
    Конкретні рейси з датами та автобусами зберігаються в моделі Trip.
    """

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Код маршруту',
        help_text='Внутрішній код, напр. UA-CZ-001',
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Назва',
        help_text='Напр.: Ужгород - Прага',
    )

    origin_country = models.CharField(max_length=2, verbose_name='Країна відправлення')
    origin_city = models.CharField(max_length=100, verbose_name='Місто відправлення')

    destination_country = models.CharField(max_length=2, verbose_name='Країна призначення')
    destination_city = models.CharField(max_length=100, verbose_name='Місто призначення')

    distance_km = models.PositiveIntegerField(verbose_name='Відстань, км')
    duration_minutes = models.PositiveIntegerField(
        verbose_name='Тривалість, хв',
        help_text='Орієнтовна тривалість поїздки у хвилинах',
    )

    description = models.TextField(blank=True, verbose_name='Опис')
    is_active = models.BooleanField(default=True, verbose_name='Активний')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Маршрут'
        verbose_name_plural = 'Маршрути'
        ordering = ['code']

    def __str__(self):
        return f'{self.code}: {self.name}'

    @property
    def duration_hours(self):
        return round(self.duration_minutes / 60, 1)


class Stop(models.Model):
    """
    Зупинка на маршруті. Маршрут має послідовність зупинок з визначеним порядком.
    Зупинки бувають з посадкою (можна сісти), з висадкою (можна вийти) або обидва.
    """

    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name='stops',
        verbose_name='Маршрут',
    )
    order = models.PositiveSmallIntegerField(
        verbose_name='№ у маршруті',
        help_text='1, 2, 3... за порядком руху',
    )

    country = models.CharField(max_length=2, verbose_name='Країна')
    city = models.CharField(max_length=100, verbose_name='Місто')
    station_name = models.CharField(max_length=200, blank=True, verbose_name='Автостанція')
    address = models.CharField(max_length=255, blank=True, verbose_name='Адреса')

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='Широта',
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='Довгота',
    )

    arrival_offset_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name='Прибуття від старту, хв',
    )
    departure_offset_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name='Відправлення від старту, хв',
    )

    can_board = models.BooleanField(default=True, verbose_name='Посадка')
    can_alight = models.BooleanField(default=True, verbose_name='Висадка')

    class Meta:
        verbose_name = 'Зупинка'
        verbose_name_plural = 'Зупинки'
        ordering = ['route', 'order']
        unique_together = [('route', 'order')]

    def __str__(self):
        return f'{self.order}. {self.city} ({self.country})'


class Trip(models.Model):
    """
    Конкретний рейс на певну дату: маршрут + автобус + водій + час відправлення.
    Саме на Trip продаються квитки та закріплюється бронювання.
    """

    class Status(models.TextChoices):
        PLANNED = 'planned', 'Запланований'
        ON_SALE = 'on_sale', 'У продажу'
        IN_PROGRESS = 'in_progress', 'У дорозі'
        COMPLETED = 'completed', 'Завершений'
        CANCELLED = 'cancelled', 'Скасований'

    class Currency(models.TextChoices):
        UAH = 'UAH', 'грн'
        EUR = 'EUR', '€'
        USD = 'USD', '$'
        PLN = 'PLN', 'zł'

    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name='trips',
        verbose_name='Маршрут',
    )
    departure_at = models.DateTimeField(verbose_name='Час відправлення')

    vehicle = models.ForeignKey(
        'fleet.Vehicle',
        on_delete=models.PROTECT,
        related_name='trips',
        limit_choices_to={
            'vehicle_type__in': ['bus', 'minibus', 'van'],
            'is_active': True,
        },
        verbose_name='Транспортний засіб',
    )
    main_driver = models.ForeignKey(
        'fleet.Driver',
        on_delete=models.PROTECT,
        related_name='trips_as_main',
        limit_choices_to={'is_available': True},
        verbose_name='Основний водій',
    )
    co_driver = models.ForeignKey(
        'fleet.Driver',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trips_as_co',
        limit_choices_to={'is_available': True},
        verbose_name='Змінний водій',
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name='Статус',
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Базова ціна квитка',
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.EUR,
        verbose_name='Валюта',
    )

    notes = models.TextField(blank=True, verbose_name='Примітки')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Рейс'
        verbose_name_plural = 'Рейси'
        ordering = ['-departure_at']

    def __str__(self):
        return f'{self.route.code} | {self.departure_at:%d.%m.%Y %H:%M}'

    @property
    def total_seats(self):
        return self.vehicle.seats_total or 0

    @property
    def sold_tickets_count(self):
        # Заглушка, поки немає модуля orders/tickets
        return 0

    @property
    def available_seats(self):
        return self.total_seats - self.sold_tickets_count
