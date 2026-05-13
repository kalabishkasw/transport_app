"""
url-маршрути клієнтського порталу.
лендінг, пошук, бронювання, оплата, gps-трекінг, кабінет,
відгуки, бонусна програма, авторизація клієнтів.
"""
from django.urls import path

from . import views


app_name = 'portal'

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('trip/<int:trip_id>/', views.trip_detail, name='trip_detail'),
    path('trip/<int:trip_id>/track/', views.trip_track, name='trip_track'),
    path('trip/<int:trip_id>/position.json', views.trip_position_api, name='trip_position_api'),
    path('book/<int:trip_id>/', views.booking_form, name='booking_form'),
    path('booking/<int:order_id>/done/', views.booking_done, name='booking_done'),
    path('booking/<int:order_id>/pay/', views.payment_form, name='payment_form'),
    path('booking/<int:order_id>/pay/process/', views.payment_process, name='payment_process'),

    path('login/', views.client_login, name='login'),
    path('register/', views.client_register, name='register'),
    path('logout/', views.client_logout, name='logout'),
    path('set-lang/<str:lang_code>/', views.set_language, name='set_language'),

    path('account/', views.account, name='account'),
    path('account/booking/<int:order_id>/', views.booking_detail, name='booking_detail'),
    path('account/booking/<int:order_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('account/booking/<int:order_id>/review/', views.leave_review, name='leave_review'),
    path('account/loyalty/', views.loyalty, name='loyalty'),
]
