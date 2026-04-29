from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Route, Stop, Trip


class StopInline(admin.TabularInline):
    """
    Інлайн для редагування зупинок прямо на сторінці маршруту.
    """
    model = Stop
    extra = 1
    fields = (
        'order',
        'country',
        'city',
        'station_name',
        'latitude',
        'longitude',
        'arrival_offset_minutes',
        'departure_offset_minutes',
        'can_board',
        'can_alight',
    )
    ordering = ('order',)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'origin_city',
        'destination_city',
        'distance_km',
        'duration_hours',
        'is_active',
        'map_link',
    )
    list_filter = ('is_active', 'origin_country', 'destination_country')
    search_fields = ('code', 'name', 'origin_city', 'destination_city')
    list_editable = ('is_active',)
    inlines = [StopInline]

    @admin.display(description='Карта')
    def map_link(self, obj):
        if not obj.pk:
            return ''
        url = reverse('core:route_map', args=[obj.pk])
        return format_html('<a href="{}" target="_blank">🗺 Карта</a>', url)

    fieldsets = (
        ('Основне', {
            'fields': ('code', 'name', 'is_active'),
        }),
        ('Маршрут', {
            'fields': (
                ('origin_country', 'origin_city'),
                ('destination_country', 'destination_city'),
                'distance_km',
                'duration_minutes',
            ),
        }),
        ('Опис', {
            'fields': ('description',),
        }),
    )


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ('route', 'order', 'city', 'country', 'station_name', 'can_board', 'can_alight')
    list_filter = ('country', 'can_board', 'can_alight')
    search_fields = ('city', 'station_name', 'route__code', 'route__name')
    ordering = ('route', 'order')


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        'route',
        'departure_at',
        'vehicle',
        'main_driver',
        'status',
        'base_price',
        'currency',
        'available_seats',
        'passenger_list_link',
    )

    @admin.display(description='Посадковий лист')
    def passenger_list_link(self, obj):
        if not obj.pk:
            return ''
        url = reverse('documents:passenger_list_pdf', args=[obj.pk])
        return format_html('<a href="{}" target="_blank">📋 PDF</a>', url)
    list_filter = ('status', 'currency', 'route')
    search_fields = ('route__code', 'route__name', 'vehicle__registration_number')
    autocomplete_fields = ('route', 'vehicle', 'main_driver', 'co_driver')
    date_hierarchy = 'departure_at'
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Рейс', {
            'fields': ('route', 'departure_at', 'status'),
        }),
        ('Транспорт та екіпаж', {
            'fields': ('vehicle', 'main_driver', 'co_driver'),
        }),
        ('Ціна', {
            'fields': ('base_price', 'currency'),
        }),
        ('Інше', {
            'fields': ('notes', 'created_at', 'updated_at'),
        }),
    )
