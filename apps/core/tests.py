"""
юніт-тести модуля core.

покриваю AutoUpdateTripStatusMiddleware - автоматичне оновлення статусів рейсів
і замовлень за часом, включно з нарахуванням балів лояльності через bulk update.

це фоновий процес (раз на 5 хвилин), і помилки тут не одразу помітні
у браузері - тому тести тут особливо корисні.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.core.middleware import AutoUpdateTripStatusMiddleware
from apps.fleet.models import Driver, Vehicle
from apps.orders.models import Order, Ticket
from apps.routes.models import Route, Stop, Trip


User = get_user_model()


def _unique():
    return uuid.uuid4().hex[:8]


def _make_basic_trip(departure_at, base_price=Decimal('60'), duration_minutes=120):
    """створюю trip з мінімальними залежностями для тестів middleware."""
    driver_user = User.objects.create_user(
        username=f'drv_{_unique()}',
        password='Test12345!secure',
        first_name='Водій', last_name='Тестовий',
    )
    driver = Driver.objects.create(
        user=driver_user,
        license_number=f'L{_unique()}',
        license_categories='D',
        license_expiry=date.today() + timedelta(days=365),
    )
    vehicle = Vehicle.objects.create(
        vehicle_type=Vehicle.VehicleType.BUS,
        registration_number=f'V{_unique()[:6].upper()}',
        brand='Mercedes', model='Test', year=2024, seats_total=20,
    )
    route = Route.objects.create(
        code=f'R-{_unique()[:6].upper()}',
        name='A - B',
        origin_country='UA', origin_city='A',
        destination_country='UA', destination_city='B',
        distance_km=100,
        duration_minutes=duration_minutes,
    )
    trip = Trip.objects.create(
        route=route, vehicle=vehicle, main_driver=driver,
        departure_at=departure_at,
        base_price=base_price,
        currency='EUR',
        status=Trip.Status.ON_SALE,
    )
    return trip




class AutoUpdateTripStatusMiddlewareTests(TestCase):
    """тести логіки автоматичного оновлення статусів рейсів."""

    def setUp(self):
        # очищую cache між тестами щоб lock middleware не блокував повторне виконання
        cache.clear()
        self.middleware = AutoUpdateTripStatusMiddleware(lambda req: None)

    def test_past_trip_becomes_completed(self):
        """якщо trip закінчився (arrival_at < now), статус має стати COMPLETED."""
        # рейс почався 3 години тому, тривалість 2 години -> вже закінчився 1 год тому
        past = timezone.now() - timedelta(hours=3)
        trip = _make_basic_trip(departure_at=past, duration_minutes=120)

        self.middleware._update_trip_statuses(timezone.now())

        trip.refresh_from_db()
        self.assertEqual(trip.status, Trip.Status.COMPLETED)

    def test_active_trip_becomes_in_progress(self):
        """якщо рейс зараз у дорозі (departure <= now < arrival), статус IN_PROGRESS."""
        # рейс почався годину тому, тривалість 4 години -> зараз у дорозі
        ongoing = timezone.now() - timedelta(hours=1)
        trip = _make_basic_trip(departure_at=ongoing, duration_minutes=240)

        self.middleware._update_trip_statuses(timezone.now())

        trip.refresh_from_db()
        self.assertEqual(trip.status, Trip.Status.IN_PROGRESS)

    def test_future_trip_status_unchanged(self):
        """рейс у майбутньому НЕ повинен переходити у IN_PROGRESS чи COMPLETED."""
        future = timezone.now() + timedelta(hours=5)
        trip = _make_basic_trip(departure_at=future)
        original_status = trip.status

        self.middleware._update_trip_statuses(timezone.now())

        trip.refresh_from_db()
        self.assertEqual(trip.status, original_status)

    def test_cancelled_trip_not_touched(self):
        """скасований рейс middleware не чіпає (статус CANCELLED фінальний)."""
        past = timezone.now() - timedelta(hours=3)
        trip = _make_basic_trip(departure_at=past, duration_minutes=60)
        trip.status = Trip.Status.CANCELLED
        trip.save()

        self.middleware._update_trip_statuses(timezone.now())

        trip.refresh_from_db()
        self.assertEqual(trip.status, Trip.Status.CANCELLED)

    def test_completing_trip_promotes_orders_and_tickets(self):
        """коли рейс стає COMPLETED, повʼязані PAID-замовлення теж COMPLETED,
        а квитки переходять у USED. це фінальний стан життєвого циклу."""
        past = timezone.now() - timedelta(hours=3)
        trip = _make_basic_trip(departure_at=past, duration_minutes=60)
        s1 = Stop.objects.create(route=trip.route, order=1, country='UA', city='A')
        s2 = Stop.objects.create(
            route=trip.route, order=2, country='UA', city='B',
            arrival_offset_minutes=60, departure_offset_minutes=60,
        )

        user = User.objects.create_user(
            username=f'buyer_{_unique()}',
            email=f'buyer_{_unique()}@example.com',
            password='Test12345!secure',
        )
        order = Order.objects.create(
            trip=trip,
            contact_first_name='Test', contact_last_name='User',
            contact_phone='+380501112233', contact_email=user.email,
            created_by=user,
            status=Order.Status.PAID,
            total_price=Decimal('60'), currency='EUR',
        )
        Ticket.objects.create(
            order=order,
            passenger_first_name='Test', passenger_last_name='User',
            document_number='X1',
            boarding_stop=s1, alighting_stop=s2,
            price=Decimal('60'),
            status=Ticket.Status.PAID,
        )

        self.middleware._update_trip_statuses(timezone.now())

        order.refresh_from_db()
        ticket = order.tickets.first()
        ticket.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertEqual(ticket.status, Ticket.Status.USED)

    def test_loyalty_points_awarded_on_completion(self):
        """коли middleware завершує рейс, нараховує бали через F-expression update.
        перевіряю що бали = total_price * LOYALTY_POINTS_PER_EUR (за default 1)."""
        past = timezone.now() - timedelta(hours=3)
        trip = _make_basic_trip(departure_at=past, duration_minutes=60)
        s1 = Stop.objects.create(route=trip.route, order=1, country='UA', city='A')
        s2 = Stop.objects.create(
            route=trip.route, order=2, country='UA', city='B',
            arrival_offset_minutes=60, departure_offset_minutes=60,
        )

        user = User.objects.create_user(
            username=f'loyal_{_unique()}',
            email=f'loyal_{_unique()}@example.com',
            password='Test12345!secure',
        )
        user.loyalty_points = 0
        user.save()

        Order.objects.create(
            trip=trip,
            contact_first_name='Test', contact_last_name='User',
            contact_phone='+380501112233', contact_email=user.email,
            created_by=user,
            status=Order.Status.PAID,
            total_price=Decimal('150'), currency='EUR',
        )

        self.middleware._update_trip_statuses(timezone.now())

        user.refresh_from_db()
        # 150 EUR * 1 (LOYALTY_POINTS_PER_EUR за default) = 150 балів
        self.assertEqual(user.loyalty_points, 150)

    def test_loyalty_not_awarded_twice_via_marker(self):
        """якщо loyalty_awarded_at вже стоїть, middleware не повинен дублювати бали.
        це критично - сигнал post_save і middleware можуть обоє намагатись нарахувати."""
        past = timezone.now() - timedelta(hours=3)
        trip = _make_basic_trip(departure_at=past, duration_minutes=60)
        s1 = Stop.objects.create(route=trip.route, order=1, country='UA', city='A')
        s2 = Stop.objects.create(
            route=trip.route, order=2, country='UA', city='B',
            arrival_offset_minutes=60, departure_offset_minutes=60,
        )

        user = User.objects.create_user(
            username=f'paid_{_unique()}',
            email=f'paid_{_unique()}@example.com',
            password='Test12345!secure',
        )
        user.loyalty_points = 0
        user.save()

        # бали уже нараховано раніше (loyalty_awarded_at вже стоїть)
        Order.objects.create(
            trip=trip,
            contact_first_name='X', contact_last_name='Y',
            contact_phone='+380501112233', contact_email=user.email,
            created_by=user,
            status=Order.Status.PAID,
            total_price=Decimal('200'), currency='EUR',
            loyalty_awarded_at=timezone.now() - timedelta(hours=1),
        )

        self.middleware._update_trip_statuses(timezone.now())

        user.refresh_from_db()
        # бали НЕ нараховано бо мітка вже стояла
        self.assertEqual(user.loyalty_points, 0)

    def test_cache_lock_prevents_double_run(self):
        """перевіряю атомарний lock через cache.add: другий виклик у короткий
        інтервал часу НЕ повинен запускати _update_trip_statuses повторно.
        це захист від race condition коли паралельні HTTP-запити приходять
        одночасно."""
        # перший виклик встановлює lock
        cache.clear()
        ran_count = {'n': 0}

        original = self.middleware._update_trip_statuses
        def counting_update(now):
            ran_count['n'] += 1
            return original(now)
        self.middleware._update_trip_statuses = counting_update

        # двічі викликаю maybe_run_update підряд
        self.middleware._maybe_run_update()
        self.middleware._maybe_run_update()

        # тільки один з двох викликів реально запустив update
        self.assertEqual(ran_count['n'], 1)
