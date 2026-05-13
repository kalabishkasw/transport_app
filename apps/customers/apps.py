"""appconfig модуля customers (юр. особи, корпоративні клієнти)"""
from django.apps import AppConfig


class CustomersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.customers'
    label = 'customers'
    verbose_name = 'Клієнти'
