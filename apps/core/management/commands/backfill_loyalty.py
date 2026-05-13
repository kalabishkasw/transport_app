"""
нараховує бали лояльності за усіма вже завершеними замовленнями, де балів
ще не нараховано. середовище раніше мало баг

логіка така, що для кожного user, у якого є COMPLETED-замовлення зі сумою > 0,
встановлюю loyalty_points = SUM(total_price * LOYALTY_POINTS_PER_EUR).
цее повне переобчислення, тому безпечно навіть якщо запусати кілька разів.

запуск:
    python manage.py backfill_loyalty
    python manage.py backfill_loyalty --dry-run
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from apps.orders.models import Order


User = get_user_model()


class Command(BaseCommand):
    help = 'Ретроактивно нараховує бали лояльності за усіма завершеними замовленнями'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Показати скільки балів буде нараховано, без запису у БД')

    def handle(self, *args, **options):
        dry = options['dry_run']
        points_per_eur = getattr(settings, 'LOYALTY_POINTS_PER_EUR', 1)

        # Сумарна виручка кожного користувача з COMPLETED-замовлень
        totals = (
            Order.objects
            .filter(status=Order.Status.COMPLETED)
            .exclude(created_by__isnull=True)
            .values('created_by')
            .annotate(total=Sum('total_price'))
            .order_by('created_by')
        )

        updated = 0
        total_points = 0

        with transaction.atomic():
            for row in totals:
                user_id = row['created_by']
                total = row['total'] or 0
                points = int(total * points_per_eur)
                if points <= 0:
                    continue

                user = User.objects.filter(pk=user_id).first()
                if not user:
                    continue

                old_points = user.loyalty_points or 0
                if old_points >= points:

                    continue

                if not dry:
                    user.loyalty_points = points
                    user.save(update_fields=['loyalty_points'])

                self.stdout.write(
                    f'User {user.username} ({user.email}): '
                    f'{old_points} -> {points} (+{points - old_points})'
                )
                updated += 1
                total_points += (points - old_points)

        if dry:
            self.stdout.write(self.style.WARNING(
                f'DRY RUN: оновлено би {updated} користувачів, +{total_points} балів сумарно.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Готово. Оновлено {updated} користувачів, нараховано {total_points} балів.'
            ))
