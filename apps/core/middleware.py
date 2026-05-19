"""
middleware:
1. CurrentUserMiddleware - зберігає поточного користувача у thread-local
   для аудит-сигналів.
2. AutoUpdateTripStatusMiddleware - автоматично оновлює статуси рейсів та
   замовлень на основі поточного часу. Спрацьовує не частіше одного разу
   на 5 хвилин (через django cache)
"""

import logging
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from .signals import set_current_user

logger = logging.getLogger(__name__)

# як часто перевіряти статуси
AUTO_UPDATE_INTERVAL_SECONDS = 300  # 5 хвилин
AUTO_UPDATE_LOCK_KEY = 'auto_update_trip_statuses_last_run'


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        set_current_user(user)
        try:
            response = self.get_response(request)
        finally:
            set_current_user(None)
        return response


class AutoUpdateTripStatusMiddleware:
    """
    перевіряє через cache чи ми не запускали оновлення
    статусів за останні AUTO_UPDATE_INTERVAL_SECONDS. Якщо ні - запускає.

    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(('/static/', '/media/', '/favicon')):
            self._maybe_run_update()
        return self.get_response(request)

    def _maybe_run_update(self):
        last_run = cache.get(AUTO_UPDATE_LOCK_KEY)
        now = timezone.now()
        if last_run is not None:

            try:
                if (now - last_run).total_seconds() < AUTO_UPDATE_INTERVAL_SECONDS:
                    return
            except TypeError:
                # last_run може бути не datetime
                pass

        # ставлю мітку ВПЕРЕД виконання, щоб паралельні запити не запускали те саме
        cache.set(AUTO_UPDATE_LOCK_KEY, now, AUTO_UPDATE_INTERVAL_SECONDS * 2)

        try:
            self._update_trip_statuses(now)
        except Exception:
            logger.exception('Auto-update trip statuses failed')

    def _update_trip_statuses(self, now):
        """
        оновлюю статуси рейсів та пов'язаних замовлень/квитків.

        не disconnect сигнали
        використовав `.update()` на queryset-ах - bulk-апдейти не викликають
        post_save/pre_save сигналів, тому email-розсилки не активуються.

        але бали лояльності нараховував вручну прямо тут, бо сигнал
        award_loyalty_points_on_completion не спрацює (теж через bulk update).
        """
        # локальні імпорти, щоб уникнути циклічних залежностей при старті Django
        from django.conf import settings as django_settings
        from django.contrib.auth import get_user_model
        from django.db import transaction
        from django.db.models import Sum

        from apps.orders.models import Order, Ticket
        from apps.routes.models import Trip

        User = get_user_model()
        points_per_eur = getattr(django_settings, 'LOYALTY_POINTS_PER_EUR', 1)

        candidates = (
            Trip.objects
            .select_related('route')
            .exclude(status__in=[Trip.Status.CANCELLED, Trip.Status.COMPLETED])
            .filter(departure_at__lte=now)
        )

        stats = {'completed': 0, 'in_progress': 0, 'loyalty_awarded': 0}

        with transaction.atomic():
            for trip in candidates:
                arrival = trip.departure_at + timedelta(
                    minutes=trip.route.duration_minutes or 0
                )

                if now >= arrival:
                    # Рейс уже завершився
                    if trip.status != Trip.Status.COMPLETED:
                        Trip.objects.filter(pk=trip.pk).update(
                            status=Trip.Status.COMPLETED,
                            updated_at=now,
                        )

                        # перед update збираємо суми балів які треба нарахувати
                        # за кожним користувачем. Беремо тільки замовлення які
                        # переходять у COMPLETED (а не вже completed) і де ще
                        # не нараховано бали (loyalty_awarded_at__isnull=True).
                        orders_to_complete = (
                            Order.objects
                            .filter(
                                trip=trip,
                                status__in=[
                                    Order.Status.PENDING,
                                    Order.Status.CONFIRMED,
                                    Order.Status.PAID,
                                    Order.Status.IN_PROGRESS,
                                ],
                                loyalty_awarded_at__isnull=True,
                            )
                            .exclude(created_by__isnull=True)
                            .values('created_by')
                            .annotate(total=Sum('total_price'))
                        )

                        # тепер оновлюємо статуси (bulk - без сигналів).
                        # одразу ставимо loyalty_awarded_at щоб post_save сигнал
                        # (якщо колись комусь захочеться окремо .save() це замовлення)
                        # не нарахував бали повторно.
                        Order.objects.filter(
                            trip=trip,
                            status__in=[
                                Order.Status.PENDING,
                                Order.Status.CONFIRMED,
                                Order.Status.PAID,
                                Order.Status.IN_PROGRESS,
                            ],
                        ).update(
                            status=Order.Status.COMPLETED,
                            loyalty_awarded_at=now,
                        )
                        Ticket.objects.filter(
                            order__trip=trip,
                            status__in=[Ticket.Status.BOOKED, Ticket.Status.PAID],
                        ).update(status=Ticket.Status.USED)

                        # нараховуємо бали кожному користувачу за його сумою.
                        # F-expression-style update щоб уникнути race condition.
                        from django.db.models import F
                        for row in orders_to_complete:
                            points = int((row['total'] or 0) * points_per_eur)
                            if points > 0:
                                User.objects.filter(pk=row['created_by']).update(
                                    loyalty_points=F('loyalty_points') + points,
                                )
                                stats['loyalty_awarded'] += points

                        stats['completed'] += 1
                elif trip.departure_at <= now < arrival:
                    # рейс у дорозі
                    if trip.status != Trip.Status.IN_PROGRESS:
                        Trip.objects.filter(pk=trip.pk).update(
                            status=Trip.Status.IN_PROGRESS,
                            updated_at=now,
                        )
                        Order.objects.filter(
                            trip=trip,
                            status=Order.Status.PAID,
                        ).update(status=Order.Status.IN_PROGRESS)
                        stats['in_progress'] += 1

        if stats['completed'] or stats['in_progress']:
            logger.info(
                'Auto-update: %d рейсів завершено, %d у дорозі, нараховано %d балів',
                stats['completed'], stats['in_progress'], stats['loyalty_awarded'],
            )
