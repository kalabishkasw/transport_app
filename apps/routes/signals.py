"""
сигнали модуля routes:
- скидаю кеш списку міст (_all_cities, _cities_with_country) при будь-якій
  зміні маршрутів або зупинок, інакше додане у admin місто зявляється на
  лендінгу і у формі пошуку аж через 10 хвилин (TTL кеша).
- каскад при скасуванні рейсу: коли диспетчер ставить Trip.status=cancelled,
  усі активні замовлення цього рейсу переводимо у REFUNDED, а квитки у CANCELLED.
"""
import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Route, Stop, Trip

logger = logging.getLogger(__name__)


CITIES_CACHE_KEYS = [
    'portal_all_cities_v1',
    'portal_cities_with_country_v1_uk',
    'portal_cities_with_country_v1_en',
]


def _flush_cities_cache():
    """видаляю всі кеш-ключі повʼязані зі списком міст."""
    for key in CITIES_CACHE_KEYS:
        cache.delete(key)


@receiver(post_save, sender=Stop)
@receiver(post_delete, sender=Stop)
def invalidate_cities_on_stop_change(sender, **kwargs):
    _flush_cities_cache()


@receiver(post_save, sender=Route)
@receiver(post_delete, sender=Route)
def invalidate_cities_on_route_change(sender, **kwargs):
    _flush_cities_cache()


@receiver(pre_save, sender=Trip)
def cascade_cancel_orders(sender, instance, **kwargs):
    """якщо рейс переходить у статус cancelled - усі активні замовлення
    на нього переходять у REFUNDED, квитки у CANCELLED.
    тут pre_save, бо нам треба зрівняти попередній статус з новим.
    bulk-update не запускає сигналів - тому це не каскадує далі."""
    if not instance.pk:
        return  # створення нового рейсу
    if instance.status != Trip.Status.CANCELLED:
        return  # цей сигнал тільки про перехід у cancelled
    try:
        previous = Trip.objects.get(pk=instance.pk)
    except Trip.DoesNotExist:
        return
    if previous.status == Trip.Status.CANCELLED:
        return  # вже був cancelled

    # імпорт локальний щоб уникнути циклічних залежностей routes <-> orders
    from apps.orders.models import Order, Ticket

    active_order_statuses = [
        Order.Status.PENDING,
        Order.Status.CONFIRMED,
        Order.Status.PAID,
        Order.Status.IN_PROGRESS,
    ]
    active_ticket_statuses = [
        Ticket.Status.BOOKED,
        Ticket.Status.PAID,
    ]

    affected_orders = Order.objects.filter(
        trip=instance, status__in=active_order_statuses,
    ).update(status=Order.Status.REFUNDED)

    affected_tickets = Ticket.objects.filter(
        order__trip=instance, status__in=active_ticket_statuses,
    ).update(status=Ticket.Status.CANCELLED)

    if affected_orders or affected_tickets:
        logger.info(
            'Рейс %s скасовано: %d замовлень у REFUNDED, %d квитків у CANCELLED',
            instance.pk, affected_orders, affected_tickets,
        )
