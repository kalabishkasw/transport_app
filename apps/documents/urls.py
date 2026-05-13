"""url-маршрути pdf-документів: квиток, посадковий лист"""
from django.urls import path

from . import views


app_name = 'documents'

urlpatterns = [
    path('ticket/<int:ticket_id>/pdf/', views.ticket_pdf, name='ticket_pdf'),
    path('trip/<int:trip_id>/passenger-list/', views.passenger_list_pdf, name='passenger_list_pdf'),
]
