from django.urls import path

from . import views


app_name = 'portal'

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('trip/<int:trip_id>/', views.trip_detail, name='trip_detail'),
    path('book/<int:trip_id>/', views.booking_form, name='booking_form'),
    path('booking/<int:order_id>/done/', views.booking_done, name='booking_done'),

    path('login/', views.client_login, name='login'),
    path('register/', views.client_register, name='register'),
    path('logout/', views.client_logout, name='logout'),

    path('account/', views.account, name='account'),
    path('account/booking/<int:order_id>/', views.booking_detail, name='booking_detail'),
]
