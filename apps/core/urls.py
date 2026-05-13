"""
url-маршрути диспетчерської панелі під /manage/.
дашборд, рейси (список/календар/деталі/експорт), замовлення, клієнти,
автопарк, водії, маршрути, звіти, журнал аудиту, ajax-сповіщення.
"""
from django.urls import path

from apps.routes.views import route_map as route_map_view

from . import views


app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('trips/', views.trips_list, name='trips_list'),
    path('trips/calendar/', views.trips_calendar, name='trips_calendar'),
    path('trips/calendar/feed/', views.trips_calendar_feed, name='trips_calendar_feed'),
    path('trips/export/', views.trips_export, name='trips_export'),
    path('trips/<int:trip_id>/', views.trip_detail, name='trip_detail'),
    path('orders/', views.orders_list, name='orders_list'),
    path('orders/export/', views.orders_export, name='orders_export'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('api/notifications/', views.notifications_data, name='notifications_data'),
    path('audit/', views.audit_log, name='audit_log'),
    path('customers/', views.customers_list, name='customers_list'),
    path('customers/<int:customer_id>/', views.customer_detail, name='customer_detail'),
    path('vehicles/', views.vehicles_list, name='vehicles_list'),
    path('drivers/', views.drivers_list, name='drivers_list'),
    path('routes/', views.routes_list, name='routes_list'),
    path('reports/', views.reports, name='reports'),
    path('routes/<int:route_id>/map/', route_map_view, name='route_map'),
]
