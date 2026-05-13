"""appconfig модуля routes (Route, Stop, Trip)"""
from django.apps import AppConfig


class RoutesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.routes'
    label = 'routes'
    verbose_name = 'Маршрути та рейси'
