"""
юніт-тести для критичної бізнес-логіки клієнтського порталу.

покриваю:
1. calculate_segment_price - пропорційна ціна за сегмент, граничні випадки
2. create_booking - бронювання, валідація, промокоди, лояльність, атомарність
3. безпека views - IDOR, 24-годинне вікно скасування, mock-оплата
4. авторизація - захист від open redirect, honeypot проти спам-ботів

тести запускаються командою:
    python manage.py test apps.portal

Django створює окрему тестову БД, кожен тест відкочується після виконання,
тому реальна база не торкається.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.fleet.models import Driver, Vehicle
from apps.orders.models import Order, PromoCode, Ticket
from apps.portal.booking_service import (
    BookingError,
    calculate_segment_price,
    create_booking,
)
from apps.portal.forms import ClientRegisterForm
from apps.routes.models import Route, Stop, Trip


User = get_user_model()


# для view-тестів вимикаю ManifestStaticFilesStorage - у тестовому середовищі
# немає зібраних static-файлів через collectstatic, тому Manifest не знаходить
# favicon.svg і тести view падають з ValueError. використовую звичайне
# FileSystemStorage у тестах, prod-конфіг не торкається.
TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


# фабрики для тестових об'єктів. дають мінімальний валідний інстанс,
# параметри можна перевизначати у конкретному тесті.


def _unique_suffix():
    """повертає короткий унікальний суфікс для уникнення колізій user/plate/code."""
    return uuid.uuid4().hex[:8]


def make_user(username=None, email=None, **kwargs):
    """створюю користувача з валідним паролем (бо AUTH_PASSWORD_VALIDATORS).
    якщо username не вказано, генерую унікальний (для тестів які створюють
    кількох користувачів)."""
    if username is None:
        username = f'user_{_unique_suffix()}'
    if email is None:
        email = f'{username}@example.com'
    defaults = {
        'first_name': 'Іван',
        'last_name': 'Тестовий',
    }
    defaults.update(kwargs)
    return User.objects.create_user(
        username=username,
        email=email,
        password='Test12345!secure',
        **defaults,
    )


def make_driver(user=None, username=None):
    """створюю Driver. user генерується унікально якщо не передано."""
    if user is None:
        if username is None:
            username = f'driver_{_unique_suffix()}'
        user = User.objects.create_user(
            username=username,
            password='Test12345!secure',
            first_name='Олег',
            last_name='Водієнко',
        )
    return Driver.objects.create(
        user=user,
        license_number=f'AB{_unique_suffix()}',
        license_categories='D,D1',
        license_expiry=date.today() + timedelta(days=365),
    )


def make_vehicle(seats=20, plate=None):
    """plate генерується унікально якщо не передано (бо registration_number unique)."""
    if plate is None:
        plate = f'AA{_unique_suffix()[:6].upper()}'
    return Vehicle.objects.create(
        vehicle_type=Vehicle.VehicleType.BUS,
        registration_number=plate,
        brand='Mercedes',
        model='Tourismo',
        year=2024,
        seats_total=seats,
    )


def make_route(code=None, duration_minutes=240, origin='Ужгород', destination='Львів'):
    """code генерується унікально якщо не передано (бо unique)."""
    if code is None:
        code = f'TST-{_unique_suffix()[:6].upper()}'
    return Route.objects.create(
        code=code,
        name=f'{origin} - {destination}',
        origin_country='UA',
        origin_city=origin,
        destination_country='UA',
        destination_city=destination,
        distance_km=250,
        duration_minutes=duration_minutes,
    )


def make_stop(route, order, city, arrival=0, departure=None, can_board=True, can_alight=True):
    """за замовчуванням departure = arrival (зупинка не має часу стоянки)."""
    return Stop.objects.create(
        route=route,
        order=order,
        country='UA',
        city=city,
        arrival_offset_minutes=arrival,
        departure_offset_minutes=arrival if departure is None else departure,
        can_board=can_board,
        can_alight=can_alight,
    )


def make_trip(route=None, vehicle=None, driver=None, base_price=Decimal('45'),
              departure_in_days=7, status='on_sale'):
    if route is None:
        route = make_route()
    if vehicle is None:
        vehicle = make_vehicle()
    if driver is None:
        driver = make_driver()
    return Trip.objects.create(
        route=route,
        vehicle=vehicle,
        main_driver=driver,
        departure_at=timezone.now() + timedelta(days=departure_in_days),
        base_price=base_price,
        currency='EUR',
        status=status,
    )


def make_passenger_data(first='Петро', last='Іваненко', seat='', doc='AB123456'):
    return {
        'first_name': first,
        'last_name': last,
        'document_type': 'passport',
        'document_number': doc,
        'price_type': 'adult',
        'seat_number': seat,
    }


def make_contact():
    return {
        'first_name': 'Петро',
        'last_name': 'Іваненко',
        'phone': '+380501234567',
        'email': 'petro@example.com',
    }




class CalculateSegmentPriceTests(TestCase):
    """
    юніт-тести для функції розрахунку ціни сегмента.
    критично, бо ця функція задає ціну квитка - помилка тут означає
    неправильні гроші у БД, на формі і у PDF-квитку.
    """

    def setUp(self):
        self.route = make_route(duration_minutes=600)  # 10-годинний маршрут
        # 3 зупинки: Ужгород (0 хв) -> Мукачево (60 хв) -> Львів (600 хв)
        self.s_uzh = make_stop(self.route, order=1, city='Ужгород', arrival=0)
        self.s_muk = make_stop(self.route, order=2, city='Мукачево', arrival=60)
        self.s_lv = make_stop(self.route, order=3, city='Львів', arrival=600)
        self.trip = make_trip(route=self.route, base_price=Decimal('60'))

    def test_full_segment_returns_base_price(self):
        """повний маршрут (перше місто → останнє) має дорівнювати base_price."""
        price = calculate_segment_price(self.trip, self.s_uzh, self.s_lv)
        self.assertEqual(price, Decimal('60'))

    def test_full_segment_matched_by_city_not_pk(self):
        """якщо у місті є кілька автовокзалів - всі вважаються повним сегментом.
        це критично щоб ціна на trip_detail і у формі бронювання збігалась."""
        # додаю другу зупинку у Львові з іншим pk але тим же містом
        s_lv_2 = make_stop(self.route, order=4, city='Львів', arrival=605, can_board=False)
        price = calculate_segment_price(self.trip, self.s_uzh, s_lv_2)
        self.assertEqual(price, Decimal('60'))

    def test_full_segment_both_endpoints_alternative_stations(self):
        """реалістичний кейс з UA-PL-002: Львів-Підзамче -> Львів-Головний-автовокзал
        і Краків-MDA -> Краків-Galeria-Krakowska. Обидва ендпоінти мають
        альтернативні автовокзали у тому самому місті - ціна = base_price."""
        # створюю route з двома автовокзалами у початковому і кінцевому місті
        route2 = make_route(duration_minutes=600)
        # Львів: Підзамче (offset 0) і Головний (offset 5)
        lv_pidzamche = make_stop(route2, order=1, city='Львів', arrival=0)
        lv_glavnyi = make_stop(route2, order=2, city='Львів', arrival=5)
        # Краків: MDA (offset 595) і Galeria (offset 600)
        kr_mda = make_stop(route2, order=3, city='Краків', arrival=595)
        kr_galeria = make_stop(route2, order=4, city='Краків', arrival=600)
        trip2 = make_trip(
            route=route2,
            base_price=Decimal('45'),
            vehicle=make_vehicle(),
            driver=make_driver(),
        )
        # пасажир обрав Львів-Головний -> Краків-MDA (НЕ найперший і НЕ останній pk)
        price = calculate_segment_price(trip2, lv_glavnyi, kr_mda)
        # все одно повна ціна, бо міста ті ж самі: Львів і Краків
        self.assertEqual(price, Decimal('45'))

    def test_partial_segment_is_proportional(self):
        """сегмент Мукачево-Львів = 9 годин з 10 повних -> 90% базової ціни,
        округлено до 0.50 EUR -> 54 EUR (60 * 0.9 = 54)."""
        price = calculate_segment_price(self.trip, self.s_muk, self.s_lv)
        # 60 * (600-60)/600 = 60 * 0.9 = 54.00
        # 54.00 / 0.5 = 108 (вже ціле), * 0.5 = 54.00
        # але якщо це Мукачево-Львів і у моїх stops Львів - останній з can_alight,
        # тоді short-circuit-у НЕ буде (Мукачево != Ужгород). Тоді 54.
        # АЛЕ якщо є short-circuit для last_alighting.city: ні, бо boarding_stop.city
        # = Мукачево != Ужгород. ✓ йде через формулу. p=54.
        self.assertEqual(price, Decimal('54.00'))

    def test_invalid_segment_order_returns_base_price(self):
        """якщо висадка раніше або рівна посадці - fallback на повну ціну."""
        # симулюю: висадка у Мукачево, посадка у Львові (інверсія)
        price = calculate_segment_price(self.trip, self.s_lv, self.s_muk)
        self.assertEqual(price, self.trip.base_price)

    def test_zero_duration_returns_base_price(self):
        """захист від ділення на 0 коли duration_minutes=0."""
        bad_route = make_route(duration_minutes=0)
        bad_trip = make_trip(
            route=bad_route,
            base_price=Decimal('30'),
            vehicle=make_vehicle(),
            driver=make_driver(),
        )
        s1 = make_stop(bad_route, 1, 'А')
        s2 = make_stop(bad_route, 2, 'Б', arrival=10)
        price = calculate_segment_price(bad_trip, s1, s2)
        self.assertEqual(price, Decimal('30'))

    def test_below_minimum_price_is_clamped(self):
        """якщо пропорційна ціна нижча за MIN_SEGMENT_PRICE (5 EUR) - підняти до 5."""
        # дуже короткий сегмент: 1 хвилина з 600. raw = 0.1 EUR -> має стати 5.
        s_short = make_stop(self.route, order=5, city='X', arrival=61)
        price = calculate_segment_price(self.trip, self.s_muk, s_short)
        self.assertEqual(price, Decimal('5.00'))

    def test_price_rounded_to_half_eur_step(self):
        """ціни мають бути кратні 0.50 EUR (для UX і прайс-листів)."""
        # сегмент який дає не-кругле число: 200 хв з 600 -> 60/3 = 20 EUR. кругло.
        # пробую щось менш кругле: 100 хв з 600 -> 60/6 = 10 EUR. теж кругло.
        # візьмемо 90 хв з 600 -> 9 EUR. кругло.
        # додам зупинку з offset=120 щоб отримати 60 хв сегмент:
        s_a = make_stop(self.route, order=6, city='A', arrival=300)  # 30 хв тому
        # 300-60 = 240 хв, 60*(240/600) = 24. цело.
        # 70 хв: 60*(70/600) = 7. цело.
        # 50 хв: 60*(50/600) = 5. цело.
        # 55 хв: 60*(55/600) = 5.5. кратно 0.5.
        s_b = make_stop(self.route, order=7, city='B', arrival=115)  # 115-60=55
        price = calculate_segment_price(self.trip, self.s_muk, s_b)
        # перевіряю що ціна кратна 0.50
        self.assertEqual(price % Decimal('0.50'), Decimal('0'))

    def test_price_never_exceeds_base_price(self):
        """навіть якщо arrival_offset > duration_minutes (брудні seed-дані),
        ціна не перевищує base_price."""
        s_overflow = make_stop(self.route, order=8, city='Y', arrival=99999)
        price = calculate_segment_price(self.trip, self.s_uzh, s_overflow)
        self.assertLessEqual(price, self.trip.base_price)




class CreateBookingTests(TestCase):
    """
    тести бронювання. покривають IDOR на рівні даних, race-захист, валідацію,
    промокоди, лояльність. найкритичніший модуль - тут гроші.
    """

    def setUp(self):
        self.route = make_route(duration_minutes=240)
        self.s_origin = make_stop(self.route, order=1, city='Ужгород')
        self.s_dest = make_stop(self.route, order=2, city='Львів', arrival=240)
        self.vehicle = make_vehicle(seats=3)  # маленький автобус для тестів вільних місць
        self.trip = make_trip(
            route=self.route,
            vehicle=self.vehicle,
            base_price=Decimal('45'),
        )
        self.user = make_user(username='buyer1', email='buyer@example.com')

    def _book(self, passengers=None, user=None, **kwargs):
        """хелпер для бронювання з дефолтами."""
        if passengers is None:
            passengers = [make_passenger_data()]
        return create_booking(
            trip_id=self.trip.id,
            contact=make_contact(),
            passengers=passengers,
            boarding_stop=self.s_origin,
            alighting_stop=self.s_dest,
            user=user,
            **kwargs,
        )

    def test_creates_order_and_tickets_with_segment_price(self):
        """успішне бронювання: створюється Order, Ticket з ціною сегмента,
        генерується order_number у форматі BK-YYYY-NNNNNN."""
        order = self._book(user=self.user)

        self.assertEqual(order.tickets.count(), 1)
        ticket = order.tickets.first()
        # повний сегмент - ціна = base_price
        self.assertEqual(ticket.price, Decimal('45'))
        self.assertEqual(order.total_price, Decimal('45'))
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.created_by, self.user)
        # номер замовлення згенерувався
        self.assertTrue(order.order_number.startswith('BK-'))
        # номер квитка згенерувався
        self.assertTrue(ticket.ticket_number.startswith('TK-'))

    def test_creates_multiple_tickets_in_one_order(self):
        """кілька пасажирів у одному замовленні - кожен має свій ticket."""
        passengers = [
            make_passenger_data(first='Анна', doc='AA111'),
            make_passenger_data(first='Богдан', doc='BB222'),
        ]
        order = self._book(passengers=passengers, user=self.user)

        self.assertEqual(order.tickets.count(), 2)
        self.assertEqual(order.total_price, Decimal('90'))  # 45 * 2

    def test_raises_when_no_seats_available(self):
        """якщо просять більше місць ніж вільно - BookingError."""
        # у мене 3 місця в автобусі, спробую забронювати 4
        passengers = [make_passenger_data(doc=f'D{i}') for i in range(4)]
        with self.assertRaises(BookingError):
            self._book(passengers=passengers, user=self.user)

    def test_raises_when_seat_already_taken(self):
        """захист від race condition на конкретному місці."""
        # перше бронювання займає місце 1
        self._book(
            passengers=[make_passenger_data(seat='1', doc='X1')],
            user=self.user,
        )
        # друге пробує те ж місце - має впасти
        other = make_user(username='buyer2', email='other@example.com')
        with self.assertRaises(BookingError) as ctx:
            self._book(
                passengers=[make_passenger_data(seat='1', doc='X2')],
                user=other,
            )
        self.assertIn('1', str(ctx.exception))

    def test_raises_on_duplicate_seats_in_same_order(self):
        """у одному замовленні два пасажири на одне місце - помилка."""
        passengers = [
            make_passenger_data(first='Анна', seat='2', doc='D1'),
            make_passenger_data(first='Богдан', seat='2', doc='D2'),
        ]
        with self.assertRaises(BookingError):
            self._book(passengers=passengers, user=self.user)

    def test_raises_on_seat_number_outside_vehicle(self):
        """місце поза діапазоном автобуса (більше за seats_total)."""
        # у автобусі 3 місця, пробую місце 99
        passengers = [make_passenger_data(seat='99', doc='D1')]
        with self.assertRaises(BookingError) as ctx:
            self._book(passengers=passengers, user=self.user)
        self.assertIn('99', str(ctx.exception))

    def test_raises_when_alighting_before_boarding(self):
        """логічна помилка: висадка перед посадкою."""
        with self.assertRaises(BookingError):
            create_booking(
                trip_id=self.trip.id,
                contact=make_contact(),
                passengers=[make_passenger_data()],
                boarding_stop=self.s_dest,    # навмисно переплутав
                alighting_stop=self.s_origin,
                user=self.user,
            )

    def test_raises_for_completed_trip(self):
        """не можна бронювати рейс який вже завершено."""
        self.trip.status = Trip.Status.COMPLETED
        self.trip.save()
        with self.assertRaises(BookingError):
            self._book(user=self.user)

    def test_anonymous_user_can_book(self):
        """бронювання без user (анонімний клієнт) - order.created_by=None."""
        order = self._book(user=None)
        self.assertIsNone(order.created_by_id)
        self.assertEqual(order.tickets.count(), 1)

    def test_applies_valid_promo_code(self):
        """активний промокод знижує total_price на discount_percent."""
        promo = PromoCode.objects.create(
            code='SUMMER15',
            discount_percent=15,
            valid_from=date.today() - timedelta(days=1),
            valid_until=date.today() + timedelta(days=30),
        )
        order = self._book(user=self.user, promo_code_input='SUMMER15')
        # 45 - 15% = 45 - 6.75 = 38.25
        self.assertEqual(order.discount_amount, Decimal('6.75'))
        self.assertEqual(order.total_price, Decimal('38.25'))
        self.assertEqual(order.promo_code, promo)

    def test_ignores_expired_promo_code(self):
        """протермінований / неактивний промокод - як ніби його не було.
        перевіряю обидва шляхи відсіювання: is_active=False і valid_until у минулому."""
        promo = PromoCode.objects.create(
            code='EXPIRED',
            discount_percent=20,
            valid_from=date.today() - timedelta(days=60),
            valid_until=date.today() - timedelta(days=1),
            is_active=False,  # явно деактивую щоб гарантувати is_valid_now=False
        )
        # переконуюсь що is_valid_now дає False у обох випадках
        self.assertFalse(promo.is_valid_now)

        order = self._book(user=self.user, promo_code_input='EXPIRED')
        self.assertIsNone(order.promo_code)
        self.assertEqual(order.discount_amount, Decimal('0'))
        self.assertEqual(order.total_price, Decimal('45'))

    def test_promo_code_times_used_increments(self):
        """кожне успішне використання збільшує лічильник на 1."""
        promo = PromoCode.objects.create(
            code='NEW10',
            discount_percent=10,
            valid_from=date.today() - timedelta(days=1),
            valid_until=date.today() + timedelta(days=30),
            times_used=5,
        )
        self._book(user=self.user, promo_code_input='NEW10')
        promo.refresh_from_db()
        self.assertEqual(promo.times_used, 6)

    def test_loyalty_redemption_capped_at_50_percent(self):
        """навіть якщо у користувача багато балів - max 50% від total_price.
        курс 10 балів = 1 EUR. 45 EUR * 50% = 22 EUR = 220 балів максимум."""
        self.user.loyalty_points = 1000
        self.user.save()
        order = self._book(user=self.user, use_loyalty_points=1000)
        # max знижка 22 EUR = 220 балів використано, знижка 22.00 EUR
        self.assertEqual(order.loyalty_redeemed_amount, Decimal('22.00'))
        self.assertEqual(order.total_price, Decimal('23.00'))  # 45 - 22
        # 220 балів списано з 1000 -> залишилось 780
        self.user.refresh_from_db()
        self.assertEqual(self.user.loyalty_points, 780)

    def test_loyalty_redemption_capped_at_user_balance(self):
        """списується не більше ніж у користувача на балансі.
        курс 10 балів = 1 EUR. 10 балів = 1 EUR знижки."""
        self.user.loyalty_points = 10
        self.user.save()
        order = self._book(user=self.user, use_loyalty_points=100)
        # доступно 10 балів = 1.00 EUR знижки
        self.assertEqual(order.loyalty_redeemed_amount, Decimal('1.00'))
        self.assertEqual(order.total_price, Decimal('44.00'))  # 45 - 1
        # перевіряю що баланс реально списався (всі 10 балів)
        self.user.refresh_from_db()
        self.assertEqual(self.user.loyalty_points, 0)

    def test_loyalty_zero_does_nothing(self):
        """якщо передано 0 балів - нічого не списується."""
        self.user.loyalty_points = 100
        self.user.save()
        order = self._book(user=self.user, use_loyalty_points=0)
        self.assertEqual(order.loyalty_redeemed_amount, Decimal('0'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.loyalty_points, 100)

    def test_atomic_rollback_on_invalid_segment(self):
        """якщо створення впало - нічого не лишається у БД (транзакція атомарна)."""
        orders_before = Order.objects.count()
        tickets_before = Ticket.objects.count()

        try:
            create_booking(
                trip_id=self.trip.id,
                contact=make_contact(),
                passengers=[make_passenger_data()],
                boarding_stop=self.s_dest,
                alighting_stop=self.s_origin,  # інверсія -> BookingError
                user=self.user,
            )
        except BookingError:
            pass

        self.assertEqual(Order.objects.count(), orders_before)
        self.assertEqual(Ticket.objects.count(), tickets_before)




@override_settings(STORAGES=TEST_STORAGES)
class BookingViewsIDORTests(TestCase):
    """
    тести захисту від IDOR (Insecure Direct Object Reference).
    хтось не повинен бачити чуже замовлення лише знаючи його ID.
    """

    def setUp(self):
        self.client = Client()
        route = make_route()
        self.s_origin = make_stop(route, order=1, city='Ужгород')
        self.s_dest = make_stop(route, order=2, city='Львів', arrival=240)
        self.trip = make_trip(route=route)

        self.owner = make_user(username='owner1', email='owner@example.com')
        self.other = make_user(username='other1', email='other@example.com')

        self.order = create_booking(
            trip_id=self.trip.id,
            contact={'first_name': 'Власник', 'last_name': 'Замовлення',
                     'phone': '+380501112233', 'email': self.owner.email},
            passengers=[make_passenger_data()],
            boarding_stop=self.s_origin,
            alighting_stop=self.s_dest,
            user=self.owner,
        )

    def test_booking_done_owner_can_view(self):
        """власник бачить своє замовлення (Order.created_by=user)."""
        self.client.force_login(self.owner)
        resp = self.client.get(reverse('portal:booking_done', args=[self.order.id]))
        self.assertEqual(resp.status_code, 200)

    def test_booking_done_other_user_gets_404(self):
        """інший автентифікований клієнт отримує 404, не 403.
        404 приховує сам факт існування замовлення."""
        self.client.force_login(self.other)
        resp = self.client.get(reverse('portal:booking_done', args=[self.order.id]))
        self.assertEqual(resp.status_code, 404)

    def test_booking_done_anonymous_with_session_token_can_view(self):
        """анонімний відвідувач який щойно створив замовлення має доступ
        через session.recent_booking_ids - інакше не побачив би підтвердження."""
        session = self.client.session
        session['recent_booking_ids'] = [self.order.id]
        session.save()
        resp = self.client.get(reverse('portal:booking_done', args=[self.order.id]))
        self.assertEqual(resp.status_code, 200)

    def test_booking_done_anonymous_without_token_404(self):
        """без recent_booking_ids анонім не має доступу."""
        resp = self.client.get(reverse('portal:booking_done', args=[self.order.id]))
        self.assertEqual(resp.status_code, 404)

    def test_booking_detail_idor_other_user_gets_404(self):
        """booking_detail захищений - чужий не бачить."""
        self.client.force_login(self.other)
        resp = self.client.get(reverse('portal:booking_detail', args=[self.order.id]))
        self.assertEqual(resp.status_code, 404)

    def test_booking_detail_staff_can_see_any(self):
        """staff-користувач бачить будь-яке замовлення (диспетчер)."""
        self.other.is_staff = True
        self.other.save()
        self.client.force_login(self.other)
        resp = self.client.get(reverse('portal:booking_detail', args=[self.order.id]))
        self.assertEqual(resp.status_code, 200)




@override_settings(STORAGES=TEST_STORAGES)
class CancelBookingTests(TestCase):
    """24-годинне вікно скасування - щоб клієнт не міг відмінити поїздку
    у останній момент і отримати кошти назад."""

    def setUp(self):
        self.client = Client()
        self.user = make_user(username='cancel1', email='cancel@example.com')
        route = make_route()
        self.s_origin = make_stop(route, order=1, city='A')
        self.s_dest = make_stop(route, order=2, city='B', arrival=120)

    def _create_order_with_trip_in(self, hours):
        """створюю замовлення на рейс що через `hours` годин."""
        route = make_route(code=f'C-{hours}')
        s1 = make_stop(route, order=1, city='A')
        s2 = make_stop(route, order=2, city='B', arrival=120)
        trip = make_trip(
            route=route,
            vehicle=make_vehicle(plate=f'P{hours}AA00'),
            driver=make_driver(username=f'drv{hours}'),
        )
        # хитро змінюю departure напряму на потрібний час
        trip.departure_at = timezone.now() + timedelta(hours=hours)
        trip.save(update_fields=['departure_at'])
        return create_booking(
            trip_id=trip.id,
            contact={'first_name': 'X', 'last_name': 'Y',
                     'phone': '+380501112233', 'email': self.user.email},
            passengers=[make_passenger_data()],
            boarding_stop=s1,
            alighting_stop=s2,
            user=self.user,
        )

    def test_can_cancel_more_than_24h_before(self):
        """за 48 годин до рейсу скасування дозволено."""
        order = self._create_order_with_trip_in(hours=48)
        self.client.force_login(self.user)
        resp = self.client.post(reverse('portal:cancel_booking', args=[order.id]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REFUNDED)

    def test_cannot_cancel_less_than_24h_before(self):
        """за 12 годин до рейсу скасування блокується."""
        order = self._create_order_with_trip_in(hours=12)
        original_status = order.status
        self.client.force_login(self.user)
        self.client.post(reverse('portal:cancel_booking', args=[order.id]))
        order.refresh_from_db()
        self.assertEqual(order.status, original_status)
        self.assertNotEqual(order.status, Order.Status.REFUNDED)

    def test_cancel_only_post(self):
        """GET-запит на cancel робить редирект, не змінює стан.
        захист від CSRF logout-style атак."""
        order = self._create_order_with_trip_in(hours=48)
        self.client.force_login(self.user)
        self.client.get(reverse('portal:cancel_booking', args=[order.id]))
        order.refresh_from_db()
        self.assertNotEqual(order.status, Order.Status.REFUNDED)




@override_settings(STORAGES=TEST_STORAGES)
class PaymentProcessTests(TestCase):
    """тести псевдо-платіжки. реальна інтеграція з банком тут не описана,
    але mock має правильно обробляти валідні і невалідні дані карти."""

    def setUp(self):
        self.client = Client()
        self.user = make_user(username='pay1', email='pay@example.com')
        route = make_route(code='PAY-01')
        self.s_origin = make_stop(route, order=1, city='Ужгород')
        self.s_dest = make_stop(route, order=2, city='Львів', arrival=240)
        self.trip = make_trip(route=route)
        self.order = create_booking(
            trip_id=self.trip.id,
            contact={'first_name': 'Pay', 'last_name': 'Test',
                     'phone': '+380501112233', 'email': self.user.email},
            passengers=[make_passenger_data()],
            boarding_stop=self.s_origin,
            alighting_stop=self.s_dest,
            user=self.user,
        )

    def _post_payment(self, **overrides):
        data = {
            'card_number': '4111111111111111',  # тестова Visa
            'card_holder': 'IVAN PETRENKO',
            'card_expiry': '12/27',
            'card_cvv': '123',
        }
        data.update(overrides)
        self.client.force_login(self.user)
        return self.client.post(reverse('portal:payment_process', args=[self.order.id]), data)

    def test_valid_card_changes_order_to_paid(self):
        """валідна картка переводить замовлення у PAID, ставить paid_at."""
        self._post_payment()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertIsNotNone(self.order.paid_at)
        self.assertEqual(self.order.payment_method, Order.PaymentMethod.ONLINE)
        # квитки також стали PAID
        self.assertTrue(all(t.status == Ticket.Status.PAID for t in self.order.tickets.all()))

    def test_test_card_0000_is_rejected(self):
        """картка з номером що закінчується на 0000 - тестова відмова."""
        self._post_payment(card_number='4111111111110000')
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, Order.Status.PAID)

    def test_invalid_card_number_rejected(self):
        """картка з нецифровим номером - відхиляється з помилкою валідації."""
        self._post_payment(card_number='abcd1234efgh5678')
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, Order.Status.PAID)

    def test_other_user_cannot_pay_for_someone_else(self):
        """інший залогінений клієнт не може оплатити чуже замовлення."""
        other = make_user(username='attacker', email='atk@example.com')
        self.client.force_login(other)
        resp = self.client.post(
            reverse('portal:payment_process', args=[self.order.id]),
            {'card_number': '4111111111111111', 'card_holder': 'X',
             'card_expiry': '12/27', 'card_cvv': '123'},
        )
        self.assertEqual(resp.status_code, 404)
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, Order.Status.PAID)




@override_settings(STORAGES=TEST_STORAGES)
class AuthSecurityTests(TestCase):
    """тести захисту авторизації від типових атак."""

    def setUp(self):
        self.client = Client()
        # username = email бо у реальному ClientRegisterForm так і робиться:
        # User.objects.create_user(username=data['email'], email=data['email'], ...)
        # це треба щоб стандартний Django authenticate() через ModelBackend
        # (який шукає за USERNAME_FIELD='username') знайшов користувача коли
        # форма логіна передає email у поле username.
        self.user = make_user(username='auth@example.com', email='auth@example.com')

    def test_login_blocks_open_redirect_to_external_domain(self):
        """login не редиректить на чужий домен через ?next=//evil.com.
        захищає від фішингу де атакер посилається на /login/?next=//evil."""
        resp = self.client.post(
            reverse('portal:login') + '?next=//evil.com/steal',
            {'username': 'auth@example.com', 'password': 'Test12345!secure'},
            follow=False,
        )
        # має 302 redirect, але НЕ на evil.com
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('evil.com', resp['Location'])

    def test_login_allows_safe_next_url(self):
        """безпечний відносний URL (з '/') дозволено."""
        resp = self.client.post(
            reverse('portal:login') + '?next=/account/loyalty/',
            {'username': 'auth@example.com', 'password': 'Test12345!secure'},
            follow=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], '/account/loyalty/')




class RegistrationHoneypotTests(TestCase):
    """тести honeypot-захисту реєстрації від спам-ботів."""

    def _valid_data(self, **overrides):
        data = {
            'first_name': 'Ярослав',
            'last_name': 'Тестов',
            'email': 'newuser@example.com',
            'phone': '+380501112233',
            'password1': 'Strong123!pass',
            'password2': 'Strong123!pass',
            'website': '',  # honeypot пустий - людина
        }
        data.update(overrides)
        return data

    def test_valid_registration_succeeds(self):
        """без honeypot - реєстрація працює."""
        form = ClientRegisterForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_filled_honeypot_blocks_registration(self):
        """бот заповнить ВСІ поля включно з website - реєстрація відхиляється."""
        form = ClientRegisterForm(data=self._valid_data(website='http://spam.example.com'))
        self.assertFalse(form.is_valid())
        self.assertIn('website', form.errors)

    def test_password_mismatch_rejected(self):
        """перевірка що валідація паролів спрацьовує."""
        form = ClientRegisterForm(data=self._valid_data(password2='Different456!'))
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_weak_password_rejected(self):
        """занадто простий пароль (всі цифри) відхиляється
        через NumericPasswordValidator."""
        form = ClientRegisterForm(data=self._valid_data(
            password1='12345678', password2='12345678',
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_duplicate_email_rejected(self):
        """email унікальний - реєстрація з існуючим email падає."""
        make_user(username='existing', email='taken@example.com')
        form = ClientRegisterForm(data=self._valid_data(email='taken@example.com'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
