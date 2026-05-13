"""
моделі автопарку: Vehicle і Driver.

Vehicle - тз (автобус, мікроавтобус, вантажівка) з характеристиками комфорту,
документами і строками техогляду/страховки.
Driver - профіль водія з посвідченням, категоріями, медоглядом і паспортом,
привязаний до User.
"""
from django.conf import settings
from django.db import models


class Vehicle(models.Model):
    """
    Транспортний засіб у автопарку. Основний акцент на пасажирські автобуси
    та мікроавтобуси, додатково вантажні авто та причепи.
    """

    class VehicleType(models.TextChoices):
        BUS = 'bus', 'Автобус'
        MINIBUS = 'minibus', 'Мікроавтобус'
        VAN = 'van', 'Мікровен'
        TRUCK = 'truck', 'Вантажівка'
        TRAILER = 'trailer', 'Причіп'

    class FuelType(models.TextChoices):
        DIESEL = 'diesel', 'Дизель'
        PETROL = 'petrol', 'Бензин'
        GAS = 'gas', 'Газ'
        ELECTRIC = 'electric', 'Електро'
        HYBRID = 'hybrid', 'Гібрид'

    class ComfortClass(models.TextChoices):
        ECONOMY = 'economy', 'Економ'
        TOURIST = 'tourist', 'Турист'
        BUSINESS = 'business', 'Бізнес'
        LUXURY = 'luxury', 'Люкс'

    # ---- спільні поля ----
    vehicle_type = models.CharField(
        max_length=10,
        choices=VehicleType.choices,
        default=VehicleType.BUS,
        verbose_name='Тип ТЗ',
    )
    registration_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Номерний знак',
    )
    brand = models.CharField(max_length=50, verbose_name='Марка')
    model = models.CharField(max_length=50, verbose_name='Модель')
    year = models.PositiveSmallIntegerField(verbose_name='Рік випуску')
    vin = models.CharField(max_length=17, blank=True, verbose_name='VIN')
    color = models.CharField(max_length=30, blank=True, verbose_name='Колір')
    fuel_type = models.CharField(
        max_length=10,
        choices=FuelType.choices,
        default=FuelType.DIESEL,
        verbose_name='Паливо',
    )
    photo = models.ImageField(upload_to='vehicles/', blank=True, null=True, verbose_name='Фото')
    mileage_km = models.PositiveIntegerField(default=0, verbose_name='Пробіг, км')

    # ---- документи ----
    date_acquired = models.DateField(blank=True, null=True, verbose_name='Дата придбання')
    insurance_expiry = models.DateField(blank=True, null=True, verbose_name='Страховка до')
    last_inspection_date = models.DateField(blank=True, null=True, verbose_name='Останній техогляд')
    next_inspection_date = models.DateField(blank=True, null=True, verbose_name='Наступний техогляд')

    # ---- характеристики автобуса (заповнюється для bus / minibus / van) ----
    seats_total = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name='Кількість пасажирських місць',
        help_text='Тільки для автобусів та мікроавтобусів.',
    )
    comfort_class = models.CharField(
        max_length=10,
        choices=ComfortClass.choices,
        blank=True,
        verbose_name='Клас комфорту',
    )
    has_wifi = models.BooleanField(default=False, verbose_name='Wi-Fi')
    has_wc = models.BooleanField(default=False, verbose_name='Туалет')
    has_climate = models.BooleanField(default=False, verbose_name='Клімат-контроль')
    has_tv = models.BooleanField(default=False, verbose_name='ТВ / мультимедіа')
    has_usb = models.BooleanField(default=False, verbose_name='USB-розетки')
    luggage_volume_m3 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Об\'єм багажника, м³',
    )

    # ---- характеристики вантажного ТЗ (для truck / trailer) ----
    capacity_tons = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Вантажопідйомність, т',
    )
    volume_m3 = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Об\'єм кузова, м³',
    )

    # ---- стан ----
    is_active = models.BooleanField(default=True, verbose_name='В експлуатації', db_index=True)
    notes = models.TextField(blank=True, verbose_name='Примітки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')

    class Meta:
        verbose_name = 'Транспортний засіб'
        verbose_name_plural = 'Транспортні засоби'
        ordering = ['vehicle_type', 'registration_number']

    def __str__(self):
        return f'{self.get_vehicle_type_display()} {self.brand} {self.model} ({self.registration_number})'

    @property
    def is_passenger(self):
        return self.vehicle_type in (
            self.VehicleType.BUS,
            self.VehicleType.MINIBUS,
            self.VehicleType.VAN,
        )


class Driver(models.Model):
    """
    Профіль водія. Прив'язаний до користувача системи з роллю «Водій».
    Зберігає посвідчення, документи та статуси.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='driver_profile',
        verbose_name='Користувач',
    )
    license_number = models.CharField(max_length=30, verbose_name='Номер посвідчення')
    license_categories = models.CharField(
        max_length=50,
        verbose_name='Категорії',
        help_text='Через кому, напр.: B, C, CE, D, D1',
    )
    license_expiry = models.DateField(verbose_name='Посвідчення дійсне до')

    date_of_birth = models.DateField(blank=True, null=True, verbose_name='Дата народження')
    date_of_hire = models.DateField(blank=True, null=True, verbose_name='Дата прийому на роботу')

    nationality = models.CharField(max_length=50, blank=True, verbose_name='Громадянство')
    passport_number = models.CharField(max_length=30, blank=True, verbose_name='Номер закордонного паспорта')
    passport_expiry = models.DateField(blank=True, null=True, verbose_name='Паспорт дійсний до')

    medical_check_expiry = models.DateField(
        blank=True,
        null=True,
        verbose_name='Медогляд до',
    )

    is_available = models.BooleanField(default=True, verbose_name='Доступний для рейсів', db_index=True)
    notes = models.TextField(blank=True, verbose_name='Примітки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')

    class Meta:
        verbose_name = 'Водій'
        verbose_name_plural = 'Водії'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return str(self.user)

    @property
    def categories_list(self):
        return [c.strip().upper() for c in self.license_categories.split(',') if c.strip()]

    @property
    def can_drive_bus(self):
        return any(c in ('D', 'D1') for c in self.categories_list)

    @property
    def can_drive_truck(self):
        return any(c in ('C', 'CE', 'C1') for c in self.categories_list)
