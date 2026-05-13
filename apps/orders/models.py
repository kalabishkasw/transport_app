"""
моделі модуля orders: PromoCode, Order, Ticket.
Order - бронювання на рейс з контактом замовника, статусом, сумою.
Ticket - окремий квиток на одного пасажира зі своїм місцем і документом.
PromoCode - знижка у відсотках з обмеженням за кількістю використань і датами.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class PromoCode(models.Model):
    """Промокод зі знижкою у відсотках. Має термін дії та ліміт використань."""

    code = models.CharField(max_length=20, unique=True, verbose_name='Код')
    description = models.CharField(max_length=200, blank=True, verbose_name='Опис')
    discount_percent = models.PositiveSmallIntegerField(
        verbose_name='Знижка, %',
        help_text='Відсоток знижки від суми замовлення',
    )
    valid_from = models.DateField(default=timezone.now, verbose_name='Діє з')
    valid_until = models.DateField(verbose_name='Діє до')
    usage_limit = models.PositiveIntegerField(
        default=0,
        verbose_name='Ліміт використань',
        help_text='0 = без обмежень',
    )
    times_used = models.PositiveIntegerField(default=0, verbose_name='Використано разів')
    is_active = models.BooleanField(default=True, verbose_name='Активний')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоди'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.code} ({self.discount_percent}%)'

    @property
    def is_valid_now(self):
        today = timezone.now().date()
        if not self.is_active:
            return False
        if self.valid_from > today or self.valid_until < today:
            return False
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False
        return True


class Order(models.Model):
    """
    Замовлення (бронювання) на конкретний рейс. Може містити один або декілька
    квитків (на різних пасажирів). Створюється диспетчером або клієнтом
    через кабінет.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Очікує підтвердження'
        CONFIRMED = 'confirmed', 'Підтверджене'
        PAID = 'paid', 'Оплачене'
        IN_PROGRESS = 'in_progress', 'Поїздка триває'
        COMPLETED = 'completed', 'Завершене'
        CANCELLED = 'cancelled', 'Скасоване'
        REFUNDED = 'refunded', 'Повернено кошти'

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Готівка'
        CARD = 'card', 'Картка'
        BANK_TRANSFER = 'bank', 'Банківський переказ'
        ONLINE = 'online', 'Онлайн'

    order_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name='Номер замовлення',
        help_text='Генерується автоматично після збереження.',
    )
    trip = models.ForeignKey(
        'routes.Trip',
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Рейс',
        db_index=True,
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Клієнт (компанія)',
        help_text='Заповнюється, якщо бронює корпоративний клієнт.',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_orders',
        verbose_name='Створив',
    )

    contact_first_name = models.CharField(max_length=64, verbose_name='Ім\'я контакту')
    contact_last_name = models.CharField(max_length=64, verbose_name='Прізвище контакту')
    contact_phone = models.CharField(max_length=30, verbose_name='Телефон')
    contact_email = models.EmailField(blank=True, verbose_name='Email')

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус',
        db_index=True,
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Загальна сума',
    )
    currency = models.CharField(max_length=3, default='EUR', verbose_name='Валюта')

    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        blank=True,
        verbose_name='Спосіб оплати',
    )
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name='Оплачено')

    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Промокод',
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Сума знижки',
    )

    notes = models.TextField(blank=True, verbose_name='Примітки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['trip', 'status']),
        ]

    def __str__(self):
        return self.order_number or f'Замовлення #{self.pk}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.order_number:
            year = self.created_at.year
            self.order_number = f'BK-{year}-{self.pk:06d}'
            super().save(update_fields=['order_number'])

    def recalculate_total(self):
        """Перерахувати загальну суму як сума цін усіх квитків мінус знижка."""
        from decimal import Decimal
        subtotal = sum((t.price for t in self.tickets.all()), start=Decimal('0'))
        discount = Decimal('0')
        if self.promo_code and self.promo_code.is_valid_now:
            discount = (subtotal * Decimal(self.promo_code.discount_percent) / Decimal(100)).quantize(Decimal('0.01'))
        self.discount_amount = discount
        self.total_price = subtotal - discount
        self.save(update_fields=['total_price', 'discount_amount', 'updated_at'])

    @property
    def tickets_count(self):
        return self.tickets.count()


class Ticket(models.Model):
    """
    Квиток. Один квиток - один пасажир.
    Належить замовленню і конкретному рейсу. Має місця посадки та висадки.
    """

    class DocumentType(models.TextChoices):
        PASSPORT = 'passport', 'Закордонний паспорт'
        ID_CARD = 'id_card', 'ID-картка'
        DRIVING = 'driving', 'Посвідчення водія'
        BIRTH = 'birth', 'Свідоцтво про народження'

    class PriceType(models.TextChoices):
        ADULT = 'adult', 'Дорослий'
        CHILD = 'child', 'Дитячий'
        STUDENT = 'student', 'Студентський'
        SENIOR = 'senior', 'Пенсійний'
        DISABLED = 'disabled', 'Пільговий'

    class Status(models.TextChoices):
        BOOKED = 'booked', 'Заброньований'
        PAID = 'paid', 'Оплачений'
        USED = 'used', 'Використаний'
        CANCELLED = 'cancelled', 'Скасований'
        REFUNDED = 'refunded', 'Повернутий'

    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name='Номер квитка',
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name='Замовлення',
    )

    passenger_first_name = models.CharField(max_length=64, verbose_name='Ім\'я пасажира')
    passenger_last_name = models.CharField(max_length=64, verbose_name='Прізвище пасажира')
    passenger_date_of_birth = models.DateField(blank=True, null=True, verbose_name='Дата народження')

    document_type = models.CharField(
        max_length=10,
        choices=DocumentType.choices,
        default=DocumentType.PASSPORT,
        verbose_name='Тип документа',
    )
    document_number = models.CharField(max_length=40, verbose_name='Номер документа')
    passenger_phone = models.CharField(max_length=30, blank=True, verbose_name='Телефон пасажира')

    boarding_stop = models.ForeignKey(
        'routes.Stop',
        on_delete=models.PROTECT,
        related_name='boarding_tickets',
        verbose_name='Місце посадки',
    )
    alighting_stop = models.ForeignKey(
        'routes.Stop',
        on_delete=models.PROTECT,
        related_name='alighting_tickets',
        verbose_name='Місце висадки',
    )
    seat_number = models.CharField(max_length=10, blank=True, verbose_name='Номер місця')

    price_type = models.CharField(
        max_length=10,
        choices=PriceType.choices,
        default=PriceType.ADULT,
        verbose_name='Тип квитка',
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Ціна',
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.BOOKED,
        verbose_name='Статус',
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Квиток'
        verbose_name_plural = 'Квитки'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
        ]

    def __str__(self):
        full_name = f'{self.passenger_last_name} {self.passenger_first_name}'.strip()
        return f'{self.ticket_number or "?"} | {full_name}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.ticket_number:
            year = self.created_at.year
            self.ticket_number = f'TK-{year}-{self.pk:06d}'
            super().save(update_fields=['ticket_number'])

    @property
    def passenger_full_name(self):
        return f'{self.passenger_last_name} {self.passenger_first_name}'.strip()
