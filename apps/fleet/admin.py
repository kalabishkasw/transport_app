from django.contrib import admin

from .models import Driver, Vehicle


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
        'is_active',
    )
    list_filter = ('vehicle_type', 'comfort_class', 'fuel_type', 'is_active')
    search_fields = ('registration_number', 'brand', 'model', 'vin')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')

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
        'license_number',
        'license_categories',
        'license_expiry',
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
