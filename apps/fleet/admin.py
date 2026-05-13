"""
адмінка автопарку: тз і водії.

виводжу кольорові бейджі з термінами дії документів (страховка, техогляд,
посвідчення, паспорт, медогляд) - червоний при простроченні, оранжевий
при наближенні. анотую queryset кількістю рейсів для сортування.
"""
from datetime import date

from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Driver, Vehicle


def _expiry_badge(d):
    """Кольоровий бейдж терміну дії документа."""
    if not d:
        return format_html('<span style="color:#94a3b8;">не вказано</span>')
    days = (d - date.today()).days
    if days < 0:
        color, label = '#dc2626', f'прострочено ({-days} дн)'
    elif days < 30:
        color, label = '#ea580c', f'{days} дн'
    elif days < 90:
        color, label = '#ca8a04', f'{days} дн'
    else:
        color, label = '#16a34a', d.strftime('%d.%m.%Y')
    return format_html('<span style="color:{}; font-weight:500;">{}</span>', color, label)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        'registration_number',
        'vehicle_type',
        'brand',
        'model',
        'year',
        'seats_total',
        'comfort_class',
        'mileage_display',
        'trips_count',
        'inspection_status',
        'is_active',
    )
    list_filter = ('vehicle_type', 'comfort_class', 'fuel_type', 'is_active')
    search_fields = ('registration_number', 'brand', 'model', 'vin')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_trips_count=Count('trips'))

    @admin.display(description='Пробіг', ordering='mileage_km')
    def mileage_display(self, obj):
        return f'{obj.mileage_km:,} км'.replace(',', ' ')

    @admin.display(description='Рейсів', ordering='_trips_count')
    def trips_count(self, obj):
        return obj._trips_count

    @admin.display(description='Техогляд до')
    def inspection_status(self, obj):
        return _expiry_badge(obj.next_inspection_date)

    fieldsets = (
        ('Основне', {
            'fields': (
                'vehicle_type',
                'registration_number',
                'brand',
                'model',
                'year',
                'vin',
                'color',
                'fuel_type',
                'photo',
                'mileage_km',
                'is_active',
            ),
        }),
        ('Документи', {
            'fields': (
                'date_acquired',
                'insurance_expiry',
                'last_inspection_date',
                'next_inspection_date',
            ),
        }),
        ('Пасажирські характеристики (автобус / мікроавтобус)', {
            'fields': (
                'seats_total',
                'comfort_class',
                'has_wifi',
                'has_wc',
                'has_climate',
                'has_tv',
                'has_usb',
                'luggage_volume_m3',
            ),
            'classes': ('collapse',),
        }),
        ('Вантажні характеристики (вантажівка / причіп)', {
            'fields': ('capacity_tons', 'volume_m3'),
            'classes': ('collapse',),
        }),
        ('Інше', {
            'fields': ('notes', 'created_at', 'updated_at'),
        }),
    )


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'phone_display',
        'license_number',
        'license_categories',
        'license_expiry_status',
        'passport_expiry_status',
        'medical_status',
        'trips_count',
        'is_available',
    )
    list_filter = ('is_available',)
    search_fields = (
        'user__last_name',
        'user__first_name',
        'license_number',
        'passport_number',
    )
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('user')
            .annotate(_trips_count=Count('trips_as_main') + Count('trips_as_co'))
        )

    @admin.display(description='Телефон')
    def phone_display(self, obj):
        return obj.user.phone or '—'

    @admin.display(description='Посвідчення до')
    def license_expiry_status(self, obj):
        return _expiry_badge(obj.license_expiry)

    @admin.display(description='Паспорт до')
    def passport_expiry_status(self, obj):
        return _expiry_badge(obj.passport_expiry)

    @admin.display(description='Медогляд до')
    def medical_status(self, obj):
        return _expiry_badge(obj.medical_check_expiry)

    @admin.display(description='Рейсів', ordering='_trips_count')
    def trips_count(self, obj):
        return obj._trips_count

    fieldsets = (
        ('Особа', {
            'fields': ('user', 'date_of_birth', 'nationality', 'is_available'),
        }),
        ('Посвідчення водія', {
            'fields': ('license_number', 'license_categories', 'license_expiry'),
        }),
        ('Закордонний паспорт', {
            'fields': ('passport_number', 'passport_expiry'),
        }),
        ('Медогляд та робота', {
            'fields': ('medical_check_expiry', 'date_of_hire'),
        }),
        ('Інше', {
            'fields': ('notes', 'created_at'),
        }),
    )
