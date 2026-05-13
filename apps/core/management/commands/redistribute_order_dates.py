"""
розтягує дати створення замовлень та квитків так, щоб вони
виглядали реалістично: люди купують квитки за 1-60 днів до рейсу.

Запуск:
    python manage.py redistribute_order_dates
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order, Ticket


class Command(BaseCommand):
    help = 'Перерозподіляє created_at у замовленнях за 1-60 днів до рейсу'

    def handle(self, *args, **options):
        now = timezone.now()

        # береемо усі замовлення з даними про рейс
        orders = Order.objects.select_related('trip').all()
        total = orders.count()
        self.stdout.write(f'Перерозподіл дат для {total} замовлень...')

        order_updates = []
        ticket_updates_map = {}  # order_id -> new created_at

        for order in orders:
            trip_dep = order.trip.departure_at

            # випадково 1-60 днів до рейсу, з годинами та хвилинами
            days_before = random.uniform(1, 60)
            offset_seconds = random.randint(0, 23 * 3600 + 59 * 60)
            new_created = trip_dep - timedelta(days=days_before, seconds=offset_seconds)

            # Не дозволяю дату створення у майбутньому.
            # замість зсуву у вузьке вікно (що дає різкий стрибок) рівномірно
            # розподіляю такі замовлення по останніх 90 днях.
            if new_created > now:
                recent_days = random.uniform(1, 90)
                new_created = now - timedelta(days=recent_days)

            # перенесення також updated_at
            order.created_at = new_created
            order.updated_at = new_created

            # якщо замовлення оплачене - paid_at пізніше за створеня
            if order.paid_at:
                order.paid_at = new_created + timedelta(
                    minutes=random.randint(5, 60),
                )

            order_updates.append(order)
            ticket_updates_map[order.id] = new_created

        # оновлюю замовлення по пакетно
        self.stdout.write('Оновлення замовлень...')
        with transaction.atomic():
            batch_size = 500
            for i in range(0, len(order_updates), batch_size):
                batch = order_updates[i:i + batch_size]
                Order.objects.bulk_update(
                    batch,
                    ['created_at', 'updated_at', 'paid_at'],
                )

        # оновлюю квитки: groupby order_id
        self.stdout.write('Оновлення квитків...')
        ticket_count = 0
        for order_id, new_date in ticket_updates_map.items():
            updated = Ticket.objects.filter(order_id=order_id).update(
                created_at=new_date,
            )
            ticket_count += updated

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Оновлено {len(order_updates)} замовлень та {ticket_count} квитків.'
        ))
