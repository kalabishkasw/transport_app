from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Ticket


@receiver(post_save, sender=Ticket)
def recalc_order_total_on_save(sender, instance, **kwargs):
    if instance.order_id:
        instance.order.recalculate_total()


@receiver(post_delete, sender=Ticket)
def recalc_order_total_on_delete(sender, instance, **kwargs):
    if instance.order_id:
        try:
            instance.order.recalculate_total()
        except Exception:
            # Замовлення могло бути видалене разом з квитком (CASCADE)
            pass
