"""appconfig модуля documents (генерація pdf: квиток, посадковий лист)"""
from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.documents'
    label = 'documents'
    verbose_name = 'Документи'
