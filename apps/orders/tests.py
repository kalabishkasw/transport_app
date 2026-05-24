"""
тести для сигналів модуля orders, зокрема нарахування балів лояльності.

ключове правило: бали мають нараховуватись РІВНО ОДИН РАЗ!! за замовлення.
для цього у моделі є поле loyalty_awarded_at - мітка часу нарахування.
сигнал award_loyalty_points_on_completion перевіряє цю мітку перш ніж
нараховувати.

окремий сценарій який потенційно міг призвести до подвійного нарахування:
middleware AutoUpdateTripStatusMiddleware через bulk update переводить
замовлення у COMPLETED і нараховує бали F-expression-style. сигнал
post_save теж би спрацюав при `.save()`, але bulk update його не запускає.
для гарантії - середовище: спершу bulk_update робить loyalty_awarded_at=now,
тоді navіть якщо хтось викличе .save() пізніше, сигнал перевірить мітку.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.fleet.models import Driver, Vehicle
from apps.orders.models import Order, Ticket
from apps.routes.models import Route, Stop, Trip


User = get_user_model()


def _setup_basic_objects(prefix='loy'):
    """мінімальна заглушка для створення замовлення."""
    user = User.objects.create_user(
        username=f'{prefix}_driver',
        password='Test12345!secure',
        first_name='Водій',
        last_name='Тестовий',
    )
    driver = Driver.objects.create(
        user=user,
        license_number=f'L{prefix}',
        license_categories='D',
        license_expiry=date.today() + timedelta(days=365),
    )
    vehicle = Vehicle.objects.create(
        vehicle_type=Vehicle.VehicleType.BUS,
        registration_number=f'V{prefix}',
        brand='Mercedes',
        model='Test',
        year=2024,
        seats_total=20,
    )
    route = Route.objects.create(
        code=f'LR-{prefix}',
        name='A - B',
        origin_country='UA', origin_city='A',
        destination_country='UA', destination_city='B',
        distance_km=100,
        duration_minutes=120,
    )
    s1 = Stop.objects.create(route=route, order=1, country='UA', city='A')
    s2 = Stop.objects.create(route=route, order=2, country='UA', city='B',
                              arrival_offset_minutes=120, departure_offset_minutes=120)
    trip = Trip.objects.create(
        route=route, vehicle=vehicle, main_driver=driver,
        departure_at=timezone.now() + timedelta(days=7),
        base_price=Decimal('50'),
        currency='EUR',
        status='on_sale',
    )
    return user, trip, s1, s2




class LoyaltyAwardSignalTests(TestCase):
    """тести сигналу award_loyalty_points_on_completion."""

    def setUp(self):
        # клієнт, на чий рахунок нараховуються бали
        self.client_user = User.objects.create_user(
            username='loy_client',
            email='loy@example.com',
            password='Test12345!secure',
        )
        self.client_user.loyalty_points = 0
        self.client_user.save()

        _, trip, s1, s2 = _setup_basic_objects('one')
        self.order = Order.objects.create(
            trip=trip,
            contact_first_name='Test', contact_last_name='User',
            contact_phone='+380501112233', contact_email='loy@example.com',
            created_by=self.client_user,
            status=Order.Status.PAID,
            total_price=Decimal('100'),
            currency='EUR',
        )
        # фейковий квиток щоб посилання було валідним
        Ticket.objects.create(
            order=self.order,
            passenger_first_name='Test', passenger_last_name='User',
            document_number='X1',
            boarding_stop=s1, alighting_stop=s2,
            price=Decimal('100'),
        )

    def test_completion_awards_points_equal_to_total_price(self):
        """при переході у COMPLETED нараховується кількість балів = total_price
        (за default 1 EUR = 1 бал)."""
        self.order.status = Order.Status.COMPLETED
        self.order.save()

        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.loyalty_points, 100)

    def test_completion_sets_loyalty_awarded_at(self):
        """після нарахування мітка часу loyalty_awarded_at заповнюється -
        захист від подвійного нарахування."""
        self.assertIsNone(self.order.loyalty_awarded_at)

        self.order.status = Order.Status.COMPLETED
        self.order.save()

        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.loyalty_awarded_at)

    def test_second_save_does_not_double_award(self):
        """якщо повторно зберегти вже завершене замовлення - бали не дублюються.
        це критично, бо адмінка може робити .save() багато разів."""
        self.order.status = Order.Status.COMPLETED
        self.order.save()

        # повторно зберігаю - не повинно нічого додати
        self.order.notes = 'оновлення нотатки'
        self.order.save()

        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.loyalty_points, 100)

    def test_award_skipped_when_already_marked(self):
        """якщо loyalty_awarded_at вже стоїть (наприклад middleware виставив
        через bulk update) - сигнал не нараховує."""
        self.order.loyalty_awarded_at = timezone.now()
        self.order.status = Order.Status.PAID
        self.order.save()

        # тепер переводжу у COMPLETED - сигнал має побачити мітку і нічого не зробити
        self.order.status = Order.Status.COMPLETED
        self.order.save()

        self.client_user.refresh_from_db()
        # бали ЗАЛИШИЛИСЬ 0 бо middleware "вже нарахував" (ми удавали)
        self.assertEqual(self.client_user.loyalty_points, 0)

    def test_no_award_for_order_without_user(self):
        """замовлення без created_by (анонімне) не може нарахувати бали."""
        anon_order = Order.objects.create(
            trip=self.order.trip,
            contact_first_name='Anon', contact_last_name='User',
            contact_phone='+380500000000', contact_email='',
            created_by=None,
            status=Order.Status.PAID,
            total_price=Decimal('50'),
            currency='EUR',
        )
        anon_order.status = Order.Status.COMPLETED
        # не повинно впасти з помилкою
        anon_order.save()

        # ніяких балів нікому не нараховано
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.loyalty_points, 0)

    def test_no_award_when_status_not_changing_to_completed(self):
        """перехід PENDING -> PAID не нараховує бали (бали тільки за COMPLETED)."""
        self.order.status = Order.Status.PAID  # вже PAID, без зміни
        self.order.save()
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.loyalty_points, 0)
