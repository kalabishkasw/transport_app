"""
сигнали для замовлень і квитків:
- автоматичний перерахунок загальної суми замовлення;
- нарахування бонусних балів при завершенні поїздки;
- лист-підтвердження клієнту після створення замовлення.
"""
import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Order, Ticket

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Ticket)
def recalc_order_total_on_save(sender, instance, **kwargs):
    if not instance.order_id:
        return
    try:
        instance.order.recalculate_total()
    except Exception:
        logger.exception(
            'Не вдалося перерахувати суму замовлення %s після збереження квитка %s',
            instance.order_id, instance.pk,
        )


@receiver(post_delete, sender=Ticket)
def recalc_order_total_on_delete(sender, instance, **kwargs):
    if not instance.order_id:
        return
    try:
        instance.order.recalculate_total()
    except Exception:
        # замовлення могло бути видалене разом з квитком - це норм
        logger.warning(
            'Перерахунок замовлення %s не виконано (можливо, видалене разом з квитком)',
            instance.order_id,
        )


@receiver(pre_save, sender=Order)
def award_loyalty_points_on_completion(sender, instance, **kwargs):
    """нараховую клієнту бонусні бали коли замовлення стає COMPLETED.
    Перевіряємо loyalty_awarded_at щоб не нарахувати двічі (наприклад якщо
    middleware вже зробив це через bulk update)."""
    if not instance.pk or not instance.created_by_id:
        return
    if instance.loyalty_awarded_at:
        # вже нараховано раніше, не дублюємо
        return
    try:
        previous = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return
    if previous.status == instance.status:
        return
    if instance.status == Order.Status.COMPLETED and previous.status != Order.Status.COMPLETED:
        # кількість балів = total_price * LOYALTY_POINTS_PER_EUR (з settings).
        # за замовчуванням 1 EUR = 1 бал.
        points_per_eur = getattr(settings, 'LOYALTY_POINTS_PER_EUR', 1)
        points = int(instance.total_price * points_per_eur)
        if points > 0:
            try:
                user = instance.created_by
                user.loyalty_points = (user.loyalty_points or 0) + points
                user.save(update_fields=['loyalty_points'])
                # ставимо мітку прямо в інстансі - перед збереженням
                # вона потрапить у БД разом зі статусом COMPLETED
                instance.loyalty_awarded_at = timezone.now()
                logger.info(
                    'Нараховано %s балів лояльності користувачу %s за замовлення %s',
                    points, user.pk, instance.order_number,
                )
            except Exception:
                logger.exception(
                    'Не вдалося нарахувати бали лояльності для замовлення %s',
                    instance.order_number,
                )


@receiver(post_save, sender=Order)
def send_order_confirmation_email(sender, instance, created, **kwargs):
    """лист-підтвердження клієнту після створення замовлення."""
    if not created or not instance.contact_email:
        return
    try:
        context = {'order': instance, 'support_email': getattr(settings, 'SUPPORT_EMAIL', '')}
        html_content = render_to_string('emails/order_confirmation.html', context)
        text_content = (
            f'Ваше замовлення {instance.order_number} створено.\n'
            f'Маршрут: {instance.trip.route.name}\n'
            f'Дата: {instance.trip.departure_at:%d.%m.%Y о %H:%M}\n'
            f'Сума: {instance.total_price} {instance.currency}\n'
        )
        msg = EmailMultiAlternatives(
            subject=f'Підтвердження замовлення {instance.order_number}, TransAuto Travel',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[instance.contact_email],
        )
        msg.attach_alternative(html_content, 'text/html')
        # fail_silently=False, але виключення ловимо нижче, щоб не зривати створення замовлення.
        msg.send(fail_silently=False)
        logger.info(
            'Лист-підтвердження для замовлення %s надіслано на %s',
            instance.order_number, instance.contact_email,
        )
    except Exception:
        logger.exception(
            'Помилка відправки листа-підтвердження для замовлення %s на адресу %s',
            instance.order_number, instance.contact_email,
        )
