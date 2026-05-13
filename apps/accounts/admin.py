"""
адмінка користувачів: розширена UserAdmin з полем ролі.

додає окремі fieldsets для додаткових полів (роль, телефон, по батькові)
на сторінці редагуваня і у формі створення користувача.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DefaultUserAdmin):
    list_display = ('username', 'last_name', 'first_name', 'role', 'email', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'last_name', 'first_name', 'email', 'phone')
    ordering = ('last_name', 'first_name')

    fieldsets = DefaultUserAdmin.fieldsets + (
        ('Додаткова інформація', {
            'fields': ('role', 'phone', 'patronymic'),
        }),
    )
    add_fieldsets = DefaultUserAdmin.add_fieldsets + (
        ('Додаткова інформація', {
            'fields': ('role', 'phone', 'patronymic', 'first_name', 'last_name', 'email'),
        }),
    )
