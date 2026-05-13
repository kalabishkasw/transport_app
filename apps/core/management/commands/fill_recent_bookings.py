"""
заповнив прогалину у графіку виручки за останні N днів додатковими замовленнями.

створює бронювання на майбутні рейси з created_at розподіленими рівномірно
за N останніх днів. Це згладжує графік виручки на дашборді диспетчера.

запуск:
    python manage.py fill_recent_bookings
    python manage.py fill_recent_bookings --days 14 --orders-per-day 80
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order, Ticket
from apps.routes.models import Trip


FIRST_NAMES_M = [
    'Олександр', 'Іван', 'Петро', 'Андрій', 'Микола', 'Сергій', 'Володимир',
    'Юрій', 'Михайло', 'Василь', 'Максим', 'Дмитро', 'Олег', 'Тарас', 'Ярослав',
]
FIRST_NAMES_F = [
    'Олена', 'Марія', 'Тетяна', 'Наталія', 'Світлана', 'Оксана', 'Ірина',
    'Юлія', 'Анна', 'Катерина', 'Ольга', 'Лариса', 'Галина', 'Вікторія',
]
LAST_NAMES = [
    'Петренко', 'Іваненко', 'Шевченко', 'Коваленко', 'Бойко', 'Ткаченко',
    'Кравченко', 'Бондаренко', 'Олійник', 'Шевчук', 'Поліщук', 'Мельник',
    'Савченко', 'Лисенко', 'Гончаренко', 'Клименко', 'Романюк', 'Паламарчук',
]


def _translit(text):
    table = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd', 'е': 'e',
        'є': 'ie', 'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'i', 'й': 'y',
        'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
        'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'shch', 'ь': '', 'ю': 'iu', 'я': 'ia',
    }
    return ''.join(table.get(c.lower(), c) for c in text)


class Command(BaseCommand):
    help = 'Створює реалістичні замовлення за останні N днів для згладжування графіка'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=14,
                            help='За скільки останніх днів створювати замовлення (default 14)')
        parser.add_argument('--orders-per-day', type=int, default=60,
                            help='Скільки замовлень на день (default 60)')

    def handle(self, *args, **options):
        now = timezone.now()
        days = options['days']
        per_day = options['orders_per_day']

        # Беру рейси у майбутньому (10-120 днів)
        future_trips = list(
            Trip.objects
            .filter(
                departure_at__gte=now + timedelta(days=2),
                departure_at__lte=now + timedelta(days=120),
                status__in=['planned', 'on_sale'],
            )
            .select_related('vehicle', 'route')
        )
        if not future_trips:
            self.stdout.write(self.style.ERROR(
                'Немає майбутніх рейсів зі статусом planned/on_sale. '
                'Спочатку запустіть seed_demo_data.'
            ))
            return

        self.stdout.write(
            f'Доступно {len(future_trips)} майбутніх рейсів. '
            f'Створюватимемо ~{days * per_day} замовлень за {days} днів...'
        )

        created = 0
        with transaction.atomic():
            for day_offset in range(days):
                # Дата created_at: останні `days` днів
                target_day = now - timedelta(days=day_offset)
                # розподіл протягом дня
                for _ in range(per_day):
                    # випадковий час всередині цього дня
                    hour = random.randint(8, 22)
                    minute = random.randint(0, 59)
                    created_at = target_day.replace(
                        hour=hour, minute=minute, second=random.randint(0, 59),
                    )
                    if created_at >= now:
                        continue

                    # випадковий рейс, у якого є вільні місця
                    trip = random.choice(future_trips)
                    seats_total = trip.vehicle.seats_total or 0
                    if seats_total <= 0:
                        continue
                    sold = Ticket.objects.filter(
                        order__trip=trip,
                        status__in=['booked', 'paid'],
                    ).count()
                    free = seats_total - sold
                    if free <= 0:
                        continue

                    # беру першу і останню зупинку для квитка
                    stops = list(trip.route.stops.all().order_by('order'))
                    if len(stops) < 2:
                        continue
                    boarding = stops[0]
                    alighting = stops[-1]


                    passengers_count = random.choices([1, 2, 3], weights=[6, 3, 1])[0]
                    passengers_count = min(passengers_count, free)

                    # контакттна особа
                    is_male = random.random() < 0.5
                    first_name = random.choice(FIRST_NAMES_M if is_male else FIRST_NAMES_F)
                    last_name = random.choice(LAST_NAMES)
                    if not is_male and not last_name.endswith('ко'):
                        last_name += 'а'

                    email = f'{_translit(first_name)}.{_translit(last_name)}{random.randint(1, 999)}@example.com'
                    phone = f'+380{random.randint(50, 99)}{random.randint(1000000, 9999999)}'

                    # статус: 60% pending, 30% confirmed, 10% paid
                    status_pick = random.random()
                    if status_pick < 0.6:
                        order_status = Order.Status.PENDING
                        ticket_status = Ticket.Status.BOOKED
                        paid_at = None
                    elif status_pick < 0.9:
                        order_status = Order.Status.CONFIRMED
                        ticket_status = Ticket.Status.BOOKED
                        paid_at = None
                    else:
                        order_status = Order.Status.PAID
                        ticket_status = Ticket.Status.PAID
                        paid_at = created_at + timedelta(minutes=random.randint(5, 60))

                    order = Order(
                        trip=trip,
                        contact_first_name=first_name,
                        contact_last_name=last_name,
                        contact_phone=phone,
                        contact_email=email,
                        status=order_status,
                        currency=trip.currency,
                        payment_method=Order.PaymentMethod.ONLINE if paid_at else '',
                        paid_at=paid_at,
                    )
                    order.save()
                    # перевизначу created_at після save
                    Order.objects.filter(pk=order.pk).update(
                        created_at=created_at,
                        updated_at=created_at,
                    )

                    # квитки
                    for _ in range(passengers_count):
                        is_p_male = random.random() < 0.5
                        p_first = random.choice(FIRST_NAMES_M if is_p_male else FIRST_NAMES_F)
                        p_last = random.choice(LAST_NAMES)
                        if not is_p_male and not p_last.endswith('ко'):
                            p_last += 'а'
                        Ticket.objects.create(
                            order=order,
                            passenger_first_name=p_first,
                            passenger_last_name=p_last,
                            document_type=Ticket.DocumentType.PASSPORT,
                            document_number=f'{random.choice(["FA","FB","FC"])}{random.randint(100000, 999999)}',
                            price_type=Ticket.PriceType.ADULT,
                            boarding_stop=boarding,
                            alighting_stop=alighting,
                            price=trip.base_price,
                            status=ticket_status,
                        )
                    created += 1

                if (day_offset + 1) % 5 == 0:
                    self.stdout.write(f'  ... створено {created} замовлень')

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Створено {created} нових замовлень за останні {days} днів. '
            f'Тепер графік виручки виглядатиме плавніше.'
        ))
