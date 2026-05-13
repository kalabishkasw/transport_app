"""
заповнення усіх рейсів реалістичними бронюваннями.
кожен рейс отримає випадкоу заповненість від 20% до 100%.

запуск:
    python manage.py seed_bookings
    python manage.py seed_bookings --reset    # видалити існуючі замовлення спочатку
"""

import random
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import post_delete, post_save

from apps.orders.models import Order, Ticket
from apps.orders.signals import (
    recalc_order_total_on_delete,
    recalc_order_total_on_save,
    send_order_confirmation_email,
)
from apps.routes.models import Trip


User = get_user_model()



# генератор реалістичних імен пасажирів

MALE_FIRST = [
    'Олександр', 'Іван', 'Петро', 'Сергій', 'Андрій', 'Михайло', 'Володимир',
    'Дмитро', 'Юрій', 'Тарас', 'Богдан', 'Артем', 'Назар', 'Олег', 'Віталій',
    'Ігор', 'Роман', 'Микола', 'Костянтин', 'Максим', 'Євген', 'Антон', 'Денис',
    'Ярослав', 'Василь', 'Степан', 'Орест', 'Остап', 'Левко',
]

FEMALE_FIRST = [
    'Олена', 'Марія', 'Анна', 'Тетяна', 'Ірина', 'Юлія', 'Світлана', 'Наталія',
    'Оксана', 'Катерина', 'Вікторія', 'Анастасія', 'Софія', 'Ангеліна', 'Дарина',
    'Христина', 'Лілія', 'Євгенія', 'Уляна', 'Зоряна', 'Аліна', 'Олександра',
    'Валерія', 'Маргарита', 'Поліна', 'Соломія', 'Богдана', 'Леся',
]

LAST_NAMES = [
    'Шевченко', 'Коваленко', 'Петренко', 'Бойко', 'Мельник', 'Ткаченко',
    'Бондаренко', 'Кравченко', 'Олійник', 'Ковальчук', 'Поліщук', 'Гриценко',
    'Попович', 'Лисенко', 'Захарченко', 'Ільченко', 'Гончар', 'Левченко',
    'Романенко', 'Григоренко', 'Сидоренко', 'Марченко', 'Кулик', 'Савчук',
    'Рудик', 'Бурлака', 'Стельмах', 'Карпенко', 'Лук\'яненко', 'Іванчук',
    'Дмитренко', 'Вовк', 'Орлик', 'Дудник', 'Каплун', 'Білозор',
]

EMAIL_DOMAINS = ['gmail.com', 'ukr.net', 'i.ua', 'meta.ua', 'outlook.com']

PHONE_PREFIXES = ['+380 67', '+380 50', '+380 95', '+380 63', '+380 73', '+380 99']


def _random_passenger():
    is_male = random.random() < 0.5
    first = random.choice(MALE_FIRST if is_male else FEMALE_FIRST)
    last = random.choice(LAST_NAMES)
    if not is_male and not last.endswith(('а', 'я', 'к', 'ч', 'л')):
        # Спрощений патерн жіночих прізвищ для деяких випадків
        pass
    return first, last


def _random_email(first, last):
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd',
        'е': 'e', 'є': 'ye', 'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i',
        'ї': 'yi', 'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ь': '', 'ю': 'yu', 'я': 'ya', "'": '',
    }
    def t(s):
        return ''.join(translit_map.get(c, c) for c in s.lower())
    return f"{t(first)}.{t(last)}{random.randint(1, 99)}@{random.choice(EMAIL_DOMAINS)}"


def _random_phone():
    return f"{random.choice(PHONE_PREFIXES)} {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}"


def _random_passport():
    letters = random.choice(['FA', 'FB', 'FC', 'EH', 'EM', 'AT'])
    return f"{letters}{random.randint(100000, 999999)}"


def _random_seat(occupied, total):
    """Вибрати випадкове місце, яке ще не зайнято."""
    available = [str(n) for n in range(1, total + 1) if str(n) not in occupied]
    if not available:
        return None
    return random.choice(available)



class Command(BaseCommand):
    help = 'Заповнює рейси реалістичними бронюваннями (20% - 100% завантаженість)'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Видалити існуючі замовлення спочатку')

    def handle(self, *args, **options):
        # Відключаємо сигнали (інакше кожен Ticket буде перераховувати Order і слати email)
        post_save.disconnect(recalc_order_total_on_save, sender=Ticket)
        post_delete.disconnect(recalc_order_total_on_delete, sender=Ticket)
        post_save.disconnect(send_order_confirmation_email, sender=Order)

        try:
            if options['reset']:
                self.stdout.write('Видалення існуючих замовлень...')
                Ticket.objects.all().delete()
                Order.objects.all().delete()

            admin = User.objects.filter(is_superuser=True).first()
            if not admin:
                self.stdout.write(self.style.ERROR(
                    'Немає суперюзера. Створи: python manage.py createsuperuser'
                ))
                return

            trips = (
                Trip.objects
                .select_related('vehicle', 'route')
                .prefetch_related('route__stops')
                .filter(vehicle__seats_total__gt=0)
            )
            total_trips = trips.count()
            self.stdout.write(f'Заповнення {total_trips} рейсів...')

            total_orders = 0
            total_tickets = 0

            for i, trip in enumerate(trips, 1):
                orders, tickets = self._fill_trip(trip, admin)
                total_orders += orders
                total_tickets += tickets

                if i % 100 == 0:
                    self.stdout.write(f'  оброблено {i}/{total_trips}, '
                                      f'замовлень {total_orders}, квитків {total_tickets}')

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(
                f'Готово. Створено {total_orders} замовлень з {total_tickets} квитками.'
            ))
        finally:
            # Повертаємо сигнали назад
            post_save.connect(recalc_order_total_on_save, sender=Ticket)
            post_delete.connect(recalc_order_total_on_delete, sender=Ticket)
            post_save.connect(send_order_confirmation_email, sender=Order)



    def _fill_trip(self, trip, admin):
        """створити замовлення для одного рейсу до випадкової заповненості."""
        seats_total = trip.vehicle.seats_total or 0
        if seats_total == 0:
            return 0, 0

        # скасовані рейси заповнюю менше (10-30%), бо люди здали квитки
        if trip.status == Trip.Status.CANCELLED:
            target_ratio = random.uniform(0.10, 0.30)
        else:
            target_ratio = random.uniform(0.20, 1.00)

        target = int(seats_total * target_ratio)
        if target < 1:
            target = 1

        stops = list(trip.route.stops.all())
        boarding_stops = [s for s in stops if s.can_board]
        alighting_stops = [s for s in stops if s.can_alight]
        if not boarding_stops or not alighting_stops:
            return 0, 0

        # статус квитків залежить від стаусу рейсу
        ticket_status_pool = self._ticket_status_pool(trip.status)

        occupied_seats = set()
        orders_count = 0
        tickets_count = 0

        while tickets_count < target:
            # розмір замовлення: переважно 1-2 пасажири, інколи 3-4 (родина)
            group_size = random.choices(
                [1, 2, 3, 4],
                weights=[55, 30, 10, 5],
            )[0]
            group_size = min(group_size, target - tickets_count)
            if group_size < 1:
                break

            # дані замовника
            contact_first, contact_last = _random_passenger()
            contact_email = _random_email(contact_first, contact_last) if random.random() < 0.7 else ''
            contact_phone = _random_phone()

            # маршрут пасажирів: обираємо посадку, висадка має бути сторго пізніше

            valid_pairs = [
                (b, a) for b in boarding_stops for a in alighting_stops
                if a.order > b.order
            ]
            if not valid_pairs:
                # маршрут з єдиною можливою зупинкою — пропустити
                break
            board, alight = random.choice(valid_pairs)

            # створюю замовлення (Order.save згенерує номер)
            with transaction.atomic():
                order = Order.objects.create(
                    trip=trip,
                    contact_first_name=contact_first,
                    contact_last_name=contact_last,
                    contact_phone=contact_phone,
                    contact_email=contact_email,
                    status=self._order_status_for(trip.status),
                    currency=trip.currency,
                    created_by=admin,
                    payment_method=random.choice(['card', 'online', 'cash', 'bank']),
                )

                # створюю квитки
                tickets_to_create = []
                order_total = Decimal('0')
                for j in range(group_size):
                    pass_first, pass_last = _random_passenger()
                    seat = _random_seat(occupied_seats, seats_total)
                    if not seat:
                        break
                    occupied_seats.add(seat)

                    # тип квитка: дорослий 80%, дитячий 10%, студент 7%, пенсіонер 3%
                    price_type = random.choices(
                        ['adult', 'child', 'student', 'senior'],
                        weights=[80, 10, 7, 3],
                    )[0]
                    # Знижки за типом
                    if price_type == 'child':
                        price = trip.base_price * Decimal('0.5')
                    elif price_type == 'student':
                        price = trip.base_price * Decimal('0.85')
                    elif price_type == 'senior':
                        price = trip.base_price * Decimal('0.9')
                    else:
                        price = trip.base_price
                    price = price.quantize(Decimal('0.01'))

                    ticket = Ticket(
                        order=order,
                        passenger_first_name=pass_first,
                        passenger_last_name=pass_last,
                        document_type='passport',
                        document_number=_random_passport(),
                        passenger_phone='',
                        boarding_stop=board,
                        alighting_stop=alight,
                        seat_number=seat,
                        price_type=price_type,
                        price=price,
                        status=random.choice(ticket_status_pool),
                        # Тимчасовий унікальний номер; нижче замінимо на TK-YYYY-NNNNNN
                        ticket_number=f'TMP-{uuid.uuid4().hex[:14]}',
                    )
                    tickets_to_create.append(ticket)
                    order_total += price

                # зберігаю квитки масово
                created_tickets = Ticket.objects.bulk_create(tickets_to_create)
                # генерую номери квитків (bulk_create не викликає save)
                for t in created_tickets:
                    t.ticket_number = f'TK-{order.created_at.year}-{t.pk:06d}'
                Ticket.objects.bulk_update(created_tickets, ['ticket_number'])

                # оновлюю суму замовлення
                order.total_price = order_total
                order.save(update_fields=['total_price'])

            tickets_count += len(created_tickets)
            orders_count += 1

        return orders_count, tickets_count

    def _order_status_for(self, trip_status):
        """статус замовлення залежно від статусу рейсу."""
        if trip_status == Trip.Status.COMPLETED:
            return random.choices(
                [Order.Status.COMPLETED, Order.Status.PAID],
                weights=[85, 15],
            )[0]
        if trip_status == Trip.Status.CANCELLED:
            return Order.Status.REFUNDED
        if trip_status == Trip.Status.IN_PROGRESS:
            return Order.Status.IN_PROGRESS
        if trip_status in (Trip.Status.ON_SALE, Trip.Status.PLANNED):
            return random.choices(
                [Order.Status.PAID, Order.Status.CONFIRMED, Order.Status.PENDING],
                weights=[70, 20, 10],
            )[0]
        return Order.Status.CONFIRMED

    def _ticket_status_pool(self, trip_status):
        """пул статусів для квитка залежно від стаусу рейсу."""
        if trip_status == Trip.Status.COMPLETED:
            return ['used', 'used', 'used', 'used', 'paid']
        if trip_status == Trip.Status.CANCELLED:
            return ['cancelled', 'cancelled', 'refunded']
        if trip_status == Trip.Status.IN_PROGRESS:
            return ['used', 'paid', 'paid']
        return ['paid', 'paid', 'paid', 'booked']
