"""
сигнали для автоматичного запису змін у AuditLog.
"""

import threading

from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.customers.models import Customer
from apps.fleet.models import Driver, Vehicle
from apps.orders.models import Order, PromoCode, Ticket
from apps.routes.models import Route, Stop, Trip

from .models import AuditLog


# тримаю посилання на поточного користувача у потоці
_thread_locals = threading.local()


def set_current_user(user):
    _thread_locals.user = user


def get_current_user():
    return getattr(_thread_locals, 'user', None)


TRACKED_MODELS = [Customer, Vehicle, Driver, Route, Stop, Trip, Order, Ticket, PromoCode]


def _model_dict(instance):
    """повертає простий dict з полів моделі (без ManyToMany та FK об'єктів)."""
    data = {}
    for f in instance._meta.fields:
        try:
            value = getattr(instance, f.attname, None)
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            data[f.name] = str(value) if value is not None else None
        except Exception:
            pass
    return data


@receiver(pre_save)
def store_old_state(sender, instance, **kwargs):
    """запам'ятати старий стан перед збереженням, щоб порахувати diff."""
    if sender not in TRACKED_MODELS:
        return
    if not instance.pk:
        instance._audit_old = None
        return
    try:
        old = sender.objects.get(pk=instance.pk)
        instance._audit_old = _model_dict(old)
    except sender.DoesNotExist:
        instance._audit_old = None


@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    if sender not in TRACKED_MODELS:
        return
    new_data = _model_dict(instance)
    changes = {}
    if created:
        action = AuditLog.Action.CREATE
        changes = {'created': True}
    else:
        action = AuditLog.Action.UPDATE
        old = getattr(instance, '_audit_old', None) or {}
        for k, v in new_data.items():
            if old.get(k) != v:
                changes[k] = {'from': old.get(k), 'to': v}
        if not changes:
            return  # нічого не змінилось

    AuditLog.objects.create(
        user=get_current_user(),
        action=action,
        model_name=sender.__name__,
        object_id=str(instance.pk),
        object_repr=str(instance)[:200],
        changes=changes,
    )


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if sender not in TRACKED_MODELS:
        return
    AuditLog.objects.create(
        user=get_current_user(),
        action=AuditLog.Action.DELETE,
        model_name=sender.__name__,
        object_id=str(instance.pk) if instance.pk else '',
        object_repr=str(instance)[:200],
        changes={},
    )
