"""url-маршрути модуля routes: тільки сторінка карти конкретного маршруту"""
from django.urls import path

from . import views


app_name = 'routes'

urlpatterns = [
    path('<int:route_id>/map/', views.route_map, name='route_map'),
]
