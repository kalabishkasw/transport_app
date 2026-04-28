from django.conf import settings
from django.db import models


class Customer(models.Model):
    """
    Клієнт компанії: юридична або фізична особа, яка замовляє перевезення.
    """

    class Country(models.TextChoices):
        UA = 'UA', 'Україна'
        PL = 'PL', 'Польща'
        DE = 'DE', 'Німеччина'
        SK = 'SK', 'Словаччина'
        HU = 'HU', 'Угорщина'
        RO = 'RO', 'Румунія'
        CZ = 'CZ', 'Чехія'
        AT = 'AT', 'Австрія'
        IT = 'IT', 'Італія'
        FR = 'FR', 'Франція'
        OTHER = 'XX', 'Інша'

    name = models.CharField(max_length=200, verbose_name='Назва (комерційна)')
    legal_name = models.CharField(max_length=255, blank=True, verbose_name='Юридична назва')
    tax_number = models.CharField(max_length=32, blank=True, verbose_name='ЄДРПОУ / податковий номер')
    vat_number = models.CharField(max_length=32, blank=True, verbose_name='VAT номер (для іноземних)')

    country = models.CharField(
        max_length=2,
        choices=Country.choices,
        default=Country.UA,
        verbose_name='Країна',
    )
    city = models.CharField(max_length=100, blank=True, verbose_name='Місто')
    address = models.CharField(max_length=255, blank=True, verbose_name='Юридична адреса')

    contact_person = models.CharField(max_length=150, blank=True, verbose_name='Контактна особа')
    contact_phone = models.CharField(max_length=30, blank=True, verbose_name='Телефон')
    contact_email = models.EmailField(blank=True, verbose_name='Email')
    website = models.URLField(blank=True, verbose_name='Сайт')

    payment_terms_days = models.PositiveSmallIntegerField(
        default=14,
        verbose_name='Відстрочка оплати, днів',
    )

    portal_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_profile',
        verbose_name='Кабінет клієнта (користувач)',
        help_text='Користувач з роллю «Клієнт», який має доступ до кабінету.',
    )

    notes = models.TextField(blank=True, verbose_name='Примітки')
    is_active = models.BooleanField(default=True, verbose_name='Активний')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')

    class Meta:
        verbose_name = 'Клієнт'
        verbose_name_plural = 'Клієнти'
        ordering = ['name']

    def __str__(self):
        return self.name
