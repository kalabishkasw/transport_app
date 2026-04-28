from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Користувач системи. Розширює стандартний AbstractUser додатковими полями
    та полем ролі. Кожна роль має окремі права у системі.
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Адміністратор'
        DISPATCHER = 'dispatcher', 'Диспетчер'
        DRIVER = 'driver', 'Водій'
        ACCOUNTANT = 'accountant', 'Бухгалтер'
        CLIENT = 'client', 'Клієнт'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.DISPATCHER,
        verbose_name='Роль',
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    patronymic = models.CharField(max_length=64, blank=True, verbose_name='По батькові')

    class Meta:
        verbose_name = 'Користувач'
        verbose_name_plural = 'Користувачі'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        full_name = f'{self.last_name} {self.first_name} {self.patronymic}'.strip()
        return full_name or self.username

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_dispatcher(self):
        return self.role == self.Role.DISPATCHER

    @property
    def is_driver(self):
        return self.role == self.Role.DRIVER

    @property
    def is_accountant(self):
        return self.role == self.Role.ACCOUNTANT

    @property
    def is_client(self):
        return self.role == self.Role.CLIENT
