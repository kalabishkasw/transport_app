"""
виправляє квитки де boarding_stop == alighting_stop або висадка раніше посадки.
перепризначав реалістичну пару (board.order < alight.order) у межах маршуту квитка.
"""

import random

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.orders.models import Ticket


class Command(BaseCommand):
    help = 'Виправляє квитки з невалідними парами посадка/висадка'

    def handle(self, *args, **options):
        # знахожу квитки де висадка не пізніше посадки за порядком
        bad = (
            Ticket.objects
            .select_related('order__trip__route', 'boarding_stop', 'alighting_stop')
            .filter(boarding_stop__order__gte=1)
        )

        # у пайтоні  фільтрую за умовою
        candidates = []
        for t in bad.iterator():
            if t.alighting_stop.order <= t.boarding_stop.order:
                candidates.append(t)

        self.stdout.write(f'Знайдено квитків для виправлення: {len(candidates)}')
        if not candidates:
            return

        # кеш stops по маршруту
        from apps.routes.models import Stop
        route_stops = {}

        fixed = 0
        with transaction.atomic():
            for t in candidates:
                route_id = t.order.trip.route_id
                if route_id not in route_stops:
                    route_stops[route_id] = list(Stop.objects.filter(route_id=route_id).order_by('order'))
                stops = route_stops[route_id]
                board_options = [s for s in stops if s.can_board]
                # Висадка має бути після посадки
                valid_pairs = [
                    (b, a) for b in board_options for a in stops
                    if a.can_alight and a.order > b.order
                ]
                if not valid_pairs:
                    continue
                b, a = random.choice(valid_pairs)
                t.boarding_stop = b
                t.alighting_stop = a
                t.save(update_fields=['boarding_stop', 'alighting_stop'])
                fixed += 1

        self.stdout.write(self.style.SUCCESS(f'Виправлено {fixed} квитків.'))
