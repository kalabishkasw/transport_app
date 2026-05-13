"""
моделі диспетчерської панелі.
тут лежить тільки AuditLog - журнал змін у ключових сутностях системи
(хто, коли, що змінив). заповнюю автоматично через сигнали post_save/post_delete.
"""
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Журнал змін у ключових моделях системи.
    Заповнюється сигналами при post_save та post_delete.
    """

    class Action(models.TextChoices):
        CREATE = 'create', 'Створено'
        UPDATE = 'update', 'Змінено'
        DELETE = 'delete', 'Видалено'

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Користувач',
    )
    action = models.CharField(max_length=10, choices=Action.choices, verbose_name='Дія')
    model_name = models.CharField(max_length=100, verbose_name='Модель')
    object_id = models.CharField(max_length=64, blank=True, verbose_name='ID об\'єкта')
    object_repr = models.CharField(max_length=200, verbose_name='Назва об\'єкта')
    changes = models.JSONField(default=dict, blank=True, verbose_name='Зміни')

    class Meta:
        verbose_name = 'Запис аудиту'
        verbose_name_plural = 'Аудит-журнал'
        ordering = ['-timestamp']

    def __str__(self):
        return f'[{self.timestamp:%d.%m.%Y %H:%M}] {self.get_action_display()} {self.model_name} #{self.object_id}'
