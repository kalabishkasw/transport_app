from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'city', 'contact_person', 'contact_phone', 'is_active')
    list_filter = ('country', 'is_active')
    search_fields = ('name', 'legal_name', 'tax_number', 'vat_number', 'contact_person', 'contact_email')
    list_editable = ('is_active',)
    autocomplete_fields = ('portal_user',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Основне', {
            'fields': ('name', 'legal_name', 'tax_number', 'vat_number', 'is_active'),
        }),
        ('Адреса', {
            'fields': ('country', 'city', 'address'),
        }),
        ('Контакти', {
            'fields': ('contact_person', 'contact_phone', 'contact_email', 'website'),
        }),
        ('Кабінет клієнта', {
            'fields': ('portal_user',),
            'classes': ('collapse',),
        }),
        ('Інше', {
            'fields': ('payment_terms_days', 'notes', 'created_at', 'updated_at'),
        }),
    )
