"""
Автоматично оновлює статуси рейсів та пов'язаних замовлень/квитків
відповідно до поточного часу.

Логіка:
  - Рейс ще не відбувся (now < departure)        - статус залишається.
  - Рейс зараз у дорозі (departure <= now < arrival): planned/on_sale -> in_progress
  - Рейс вже завершився (now >= arrival):       planned/on_sale/in_progress -> completed
  - Скасовані рейси (cancelled) залишаються без змін.

Для замовлень:
  - Якщо рейс став completed: confirmed/pending/paid -> completed; квитки -> used
  - Якщо рейс став in_progress: paid -> in_progress (інші не чіпаємо)

Запуск:
    python manage.py update_trip_statuses
    python manage.py update_trip_statuses --dry-run    # без запису, лише звіт
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.utils import timezone

from apps.orders.models import Order, Ticket
from apps.orders.signals import (
    award_loyalty_points_on_completion,
    send_order_confirmation_email,
)
from apps.routes.models import Trip


class Command(BaseCommand):
    help = 'Автоматично оновлює статуси рейсів та замовлень'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Показати, що буде змінено, без запису у БД')

    def handle(self, *args, **options):
        dry = options['dry_run']
        now = timezone.now()

        # Тимчасово відключаємо сигнали (інакше для тисяч замовлень
        # буде відправлено лист і нараховано бали)
        post_save.disconnect(send_order_confirmation_email, sender=Order)
        pre_save.disconnect(award_loyalty_points_on_completion, sender=Order)

        try:
            stats = {
                'trips_to_completed': 0,
                'trips_to_in_progress': 0,
                'orders_to_completed': 0,
                'orders_to_in_progress': 0,
                'tickets_to_used': 0,
            }

            # Усі рейси з їх маршрутами (потрібна тривалість)
            trips = Trip.objects.select_related('route').exclude(
                status__in=[Trip.Status.CANCELLED, Trip.Status.COMPLETED]
            )

            with transaction.atomic():
                for trip in trips:
                    arrival = trip.departure_at + timedelta(minutes=trip.route.duration_minutes)

                    if now >= arrival:
                        # Рейс вже завершився
                        new_status = Trip.Status.COMPLETED
                        if trip.status != new_status:
                            stats['trips_to_completed'] += 1
                            if not dry:
                                trip.status = new_status
                                trip.save(update_fields=['status', 'updated_at'])

                                # Замовлення -> completed, квитки -> used
                                affected_orders = Order.objects.filter(
                                    trip=trip,
                                    status__in=[
                                        Order.Status.PENDING,
                                        Order.Status.CONFIRMED,
                                        Order.Status.PAID,
                                        Order.Status.IN_PROGRESS,
                                    ],
                                )
                                stats['orders_to_completed'] += affected_orders.count()
                                affected_orders.update(status=Order.Status.COMPLETED)

                                tickets_changed = Ticket.objects.filter(
                                    order__trip=trip,
                                    status__in=[Ticket.Status.BOOKED, Ticket.Status.PAID],
                                ).update(status=Ticket.Status.USED)
                                stats['tickets_to_used'] += tickets_changed

                    elif trip.departure_at <= now < arrival:
                        # Рейс у дорозі
                        new_status = Trip.Status.IN_PROGRESS
                        if trip.status != new_status:
                            stats['trips_to_in_progress'] += 1
                            if not dry:
                                trip.status = new_status
                                trip.save(update_fields=['status', 'updated_at'])

                                affected_orders = Order.objects.filter(
                                    trip=trip,
                                    status=Order.Status.PAID,
                                )
                                stats['orders_to_in_progress'] += affected_orders.count()
                                affected_orders.update(status=Order.Status.IN_PROGRESS)

            self.stdout.write('')
            if dry:
                self.stdout.write(self.style.WARNING('DRY RUN: змін у БД не зроблено.'))
            self.stdout.write(self.style.SUCCESS(
                f"Рейси -> Завершено:    {stats['trips_to_completed']}\n"
                f"Рейси -> У дорозі:     {stats['trips_to_in_progress']}\n"
                f"Замовлення -> Завершено: {stats['orders_to_completed']}\n"
                f"Замовлення -> У дорозі:  {stats['orders_to_in_progress']}\n"
                f"Квитки -> Використано:   {stats['tickets_to_used']}\n"
            ))

        finally:
            post_save.connect(send_order_confirmation_email, sender=Order)
            pre_save.connect(award_loyalty_points_on_completion, sender=Order)
