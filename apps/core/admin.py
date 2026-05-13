"""
адмінка диспетчерської: тільки журнал аудиту (read-only для всіх ролей).
записи створюються автоматично через сигнали, ручне додвання заборонив
"""
from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_repr')
    list_filter = ('action', 'model_name', 'user')
    search_fields = ('object_repr', 'object_id', 'model_name')
    readonly_fields = ('timestamp', 'user', 'action', 'model_name', 'object_id', 'object_repr', 'changes')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
