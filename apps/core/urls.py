from django.urls import path

from apps.routes.views import route_map as route_map_view

from . import views


app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('trips/', views.trips_list, name='trips_list'),
    path('trips/<int:trip_id>/', views.trip_detail, name='trip_detail'),
    path('orders/', views.orders_list, name='orders_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('customers/', views.customers_list, name='customers_list'),
    path('vehicles/', views.vehicles_list, name='vehicles_list'),
    path('drivers/', views.drivers_list, name='drivers_list'),
    path('routes/', views.routes_list, name='routes_list'),
    path('routes/<int:route_id>/map/', route_map_view, name='route_map'),
]
