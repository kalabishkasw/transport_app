from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Order, Ticket


class TicketInline(admin.TabularInline):
    """
    Інлайн для додавання квитків прямо у формі замовлення.
    """
    model = Ticket
    extra = 1
    fields = (
        'ticket_number',
        'passenger_last_name',
        'passenger_first_name',
        'document_number',
        'boarding_stop',
        'alighting_stop',
        'seat_number',
        'price_type',
        'price',
        'status',
    )
    readonly_fields = ('ticket_number',)
    autocomplete_fields = ('boarding_stop', 'alighting_stop')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'trip',
        'customer',
        'contact_last_name',
        'contact_first_name',
        'tickets_count',
        'total_price',
        'currency',
        'status',
        'created_at',
    )
    list_filter = ('status', 'payment_method', 'currency', 'trip__route')
    search_fields = (
        'order_number',
        'contact_last_name',
        'contact_first_name',
        'contact_phone',
        'contact_email',
        'customer__name',
    )
    autocomplete_fields = ('trip', 'customer', 'created_by')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [TicketInline]
    actions = ['recalc_totals']

    fieldsets = (
        ('Замовлення', {
            'fields': ('order_number', 'trip', 'status'),
        }),
        ('Замовник', {
            'fields': (
                'customer',
                ('contact_last_name', 'contact_first_name'),
                ('contact_phone', 'contact_email'),
            ),
        }),
        ('Оплата', {
            'fields': (('total_price', 'currency'), 'payment_method', 'paid_at'),
        }),
        ('Інше', {
            'fields': ('created_by', 'notes', 'created_at', 'updated_at'),
        }),
    )

    @admin.action(description='Перерахувати загальну суму з квитків')
    def recalc_totals(self, request, queryset):
        for order in queryset:
            order.recalculate_total()
        self.message_user(request, f'Перераховано {queryset.count()} замовлень')

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_number',
        'passenger_last_name',
        'passenger_first_name',
        'order',
        'boarding_stop',
        'alighting_stop',
        'seat_number',
        'price_type',
        'price',
        'status',
        'pdf_link',
    )
    list_filter = ('status', 'price_type', 'document_type')
    search_fields = (
        'ticket_number',
        'passenger_last_name',
        'passenger_first_name',
        'document_number',
        'order__order_number',
    )
    autocomplete_fields = ('order', 'boarding_stop', 'alighting_stop')
    readonly_fields = ('ticket_number', 'created_at')

    @admin.display(description='PDF')
    def pdf_link(self, obj):
        if not obj.pk:
            return ''
        url = reverse('documents:ticket_pdf', args=[obj.pk])
        return format_html('<a href="{}" target="_blank">📄 Квиток</a>', url)
