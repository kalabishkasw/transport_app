"""
адмінка модуля routes: Route, Stop (inline у Route), Trip.
показую відсоток заповненості, виручку, налаштовую статус-бейджі і фільтри.
"""
from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import Count, Q, Sum
from django.urls import reverse
from django.utils.html import format_html

from .models import Route, Stop, Trip


class StopInline(admin.TabularInline):
    """
    інлайн для редагування зупинок прямо на сторінці маршруту.
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
        'stops_count_display',
        'trips_count_display',
        'is_active',
        'map_link',
    )
    list_filter = ('is_active', 'origin_country', 'destination_country')
    search_fields = ('code', 'name', 'origin_city', 'destination_city')
    list_editable = ('is_active',)
    inlines = [StopInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _stops_count=Count('stops', distinct=True),
            _trips_count=Count('trips', distinct=True),
        )

    @admin.display(description='Зупинок', ordering='_stops_count')
    def stops_count_display(self, obj):
        return obj._stops_count

    @admin.display(description='Рейсів', ordering='_trips_count')
    def trips_count_display(self, obj):
        return obj._trips_count

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
        'occupancy_display',
        'revenue_display',
        'base_price',
        'currency',
        'passenger_list_link',
    )
    list_filter = ('status', 'currency', 'route')
    search_fields = ('route__code', 'route__name', 'vehicle__registration_number')
    autocomplete_fields = ('route', 'vehicle', 'main_driver', 'co_driver')
    date_hierarchy = 'departure_at'
    readonly_fields = ('created_at', 'updated_at')
    actions = ['duplicate_to_next_week', 'duplicate_to_next_month', 'mark_on_sale', 'mark_completed']

    @admin.action(description='Дублювати на наступний тиждень')
    def duplicate_to_next_week(self, request, queryset):
        self._duplicate_trips(queryset, days=7, request=request)

    @admin.action(description='Дублювати на наступний місяць (через 30 днів)')
    def duplicate_to_next_month(self, request, queryset):
        self._duplicate_trips(queryset, days=30, request=request)

    @admin.action(description='Виставити статус "У продажу"')
    def mark_on_sale(self, request, queryset):
        updated = queryset.update(status=Trip.Status.ON_SALE)
        self.message_user(request, f'Оновлено рейсів: {updated}.')

    @admin.action(description='Виставити статус "Завершено"')
    def mark_completed(self, request, queryset):
        updated = queryset.update(status=Trip.Status.COMPLETED)
        self.message_user(request, f'Оновлено рейсів: {updated}.')

    def _duplicate_trips(self, queryset, days, request):
        created = 0
        for trip in queryset:
            Trip.objects.create(
                route=trip.route,
                departure_at=trip.departure_at + timedelta(days=days),
                vehicle=trip.vehicle,
                main_driver=trip.main_driver,
                co_driver=trip.co_driver,
                status=Trip.Status.PLANNED,
                base_price=trip.base_price,
                currency=trip.currency,
                notes=trip.notes,
            )
            created += 1
        self.message_user(
            request,
            f'Створено {created} нових рейсів через {days} днів.',
            level=messages.SUCCESS,
        )

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

    def get_queryset(self, request):
        active_ticket_filter = Q(orders__tickets__status__in=['booked', 'paid', 'used'])
        return (
            super().get_queryset(request)
            .select_related('route', 'vehicle', 'main_driver__user')
            .annotate(
                _sold=Count('orders__tickets', filter=active_ticket_filter, distinct=True),
                _revenue=Sum(
                    'orders__tickets__price',
                    filter=active_ticket_filter,
                ),
            )
        )

    @admin.display(description='Заповненість', ordering='_sold')
    def occupancy_display(self, obj):
        sold = obj._sold or 0
        total = obj.vehicle.seats_total or 0
        if total == 0:
            return format_html('<span style="color:#94a3b8;">—</span>')
        ratio = sold / total
        if ratio >= 0.8:
            color = '#dc2626'
        elif ratio >= 0.5:
            color = '#ca8a04'
        else:
            color = '#16a34a'
        return format_html(
            '<span style="color:{}; font-weight:500;">{}/{} ({}%)</span>',
            color, sold, total, int(ratio * 100),
        )

    @admin.display(description='Виручка', ordering='_revenue')
    def revenue_display(self, obj):
        rev = obj._revenue or 0
        return f'{rev} {obj.currency}' if rev else '—'

    @admin.display(description='Посадковий лист')
    def passenger_list_link(self, obj):
        if not obj.pk:
            return ''
        url = reverse('documents:passenger_list_pdf', args=[obj.pk])
        return format_html('<a href="{}" target="_blank">📋 PDF</a>', url)
