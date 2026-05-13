"""
адмінка відгуків: модерую через is_published, фільтри за оцінкою,
пошук за текстом і користувачем/маршрутом.
"""
from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('trip', 'user', 'rating', 'title', 'is_published', 'created_at')
    list_filter = ('rating', 'is_published')
    search_fields = ('title', 'comment', 'user__last_name', 'user__first_name', 'trip__route__code')
    list_editable = ('is_published',)
    autocomplete_fields = ('trip', 'user', 'order')
    readonly_fields = ('created_at',)
