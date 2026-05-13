"""appconfig диспетчерської панелі. у ready() підключаю audit-сигнали"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    label = 'core'
    verbose_name = 'Веб-інтерфейс диспетчера'

    def ready(self):
        from . import signals  # noqa: F401
