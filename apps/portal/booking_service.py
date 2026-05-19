"""
сервіс бронювання. виношу бізнес-логіку з view, забезпечую транзакційну
цілісність і захист від race conditions при паралельних бронюваннях.

використовую SELECT FOR UPDATE на Trip і PromoCode щоб гарантувати:
- два клієнти не куплять одне останнє місце,
- ліміт використань промокоду не буде перевищено.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.orders.models import Order, PromoCode, Ticket
from apps.routes.models import Stop, Trip


class BookingError(Exception):
    """бізнесова помилка під час бронювання (для виводу користувачу)."""


User = get_user_model()


@transaction.atomic
def create_booking(
    *,
    trip_id: int,
    contact: dict,
    passengers: Iterable[dict],
    boarding_stop: Stop,
    alighting_stop: Stop,
    user=None,
    promo_code_input: str = '',
    use_loyalty_points: int = 0,
) -> Order:
    """
    створює замовлення на рейс з передачею списку пасажирів.

    параметри
    ---------
    trip_id : int
        ID рейсу (буде заблокований SELECT FOR UPDATE).
    contact : dict
        first_name, last_name, phone, email — контактна особа замовлення.
    passengers : iterable of dict
        Кожний словник: first_name, last_name, document_type, document_number,
        price_type, seat_number (опц.).
    boarding_stop, alighting_stop : Stop
        Пункти посадки і висадки. Мають належати маршруту рейсу і
        boarding.order < alighting.order.
    user : User or None
        Авторизований користувач (для нарахування лояльності).
    promo_code_input : str
        Введений код. Якщо знайдено активний - застосовується.
    use_loyalty_points : int
        Скільки балів використати (1 бал = 1 EUR, максимум 50% суми).

    повертає
    --------
    Order
        Створене замовлення зі згенерованим order_number, перерахованою сумою.

    викидає
    -------
    BookingError
        Якщо немає вільних місць, маршрут зупинок невалідний, рейс недоступний.
    """
    passengers = list(passengers)
    if not passengers:
        raise BookingError('Список пасажирів порожній.')

    # 1. блокуємо рейс. інші транзакції чекатимуть
    try:
        trip = Trip.objects.select_for_update().select_related('vehicle', 'route').get(pk=trip_id)
    except Trip.DoesNotExist:
        raise BookingError('Рейс не знайдено.')

    if trip.status not in ('on_sale', 'planned'):
        raise BookingError('Рейс недоступний для бронювання.')

    # 2. перевірка коректності зупинок
    if boarding_stop.route_id != trip.route_id or alighting_stop.route_id != trip.route_id:
        raise BookingError('Зупинки не належать маршруту цього рейсу.')
    if alighting_stop.order <= boarding_stop.order:
        raise BookingError('Пункт висадки має бути після пункту посадки.')

    # 3. перевіряємо вільні місця всерединнні блокування
    sold = Ticket.objects.filter(
        order__trip=trip,
        status__in=['booked', 'paid'],
    ).count()
    seats_total = trip.vehicle.seats_total or 0
    free = max(0, seats_total - sold)
    if len(passengers) > free:
        raise BookingError(
            f'На рейсі залишилось лише {free} вільн{"е місце" if free == 1 else "их місць"}, '
            f'а ви намагаєтесь забронювати {len(passengers)}.'
        )

    # 4. перевірка зайнятих місць (щоб два клієнти не отримали одне місце).
    requested_seats = [p.get('seat_number', '').strip() for p in passengers if p.get('seat_number', '').strip()]

    # перевіряю що всі вказані місця у межах автобуса.
    # форма вже гарантує що це цифри, лишилось обмежити верхньою межею.
    if requested_seats and seats_total > 0:
        for s in requested_seats:
            try:
                if int(s) > seats_total:
                    raise BookingError(
                        f'Місце {s} не існує. У цьому автобусі лише {seats_total} місць.'
                    )
            except ValueError:
                raise BookingError(f'Невірний номер місця: {s}.')

    if requested_seats:
        occupied = set(
            Ticket.objects.filter(
                order__trip=trip,
                status__in=['booked', 'paid'],
            )
            .exclude(seat_number='')
            .values_list('seat_number', flat=True)
        )
        clash = [s for s in requested_seats if s in occupied]
        if clash:
            raise BookingError(
                f'Місц{"е" if len(clash) == 1 else "я"} {", ".join(clash)} вже зайнят{"е" if len(clash) == 1 else "і"}.'
            )
        # перевірка дублювання у самому замовленні
        if len(requested_seats) != len(set(requested_seats)):
            raise BookingError('У замовленні є пасажири з однаковими номерами місць.')

    # 5. промокод (теж під замком).
    promo_code_obj: Optional[PromoCode] = None
    if promo_code_input:
        try:
            promo_code_obj = (
                PromoCode.objects.select_for_update().get(code__iexact=promo_code_input)
            )
        except PromoCode.DoesNotExist:
            promo_code_obj = None

        if promo_code_obj and not promo_code_obj.is_valid_now:
            promo_code_obj = None

    # 6. створюю замовлення
    order = Order.objects.create(
        trip=trip,
        contact_first_name=contact['first_name'],
        contact_last_name=contact['last_name'],
        contact_phone=contact['phone'],
        contact_email=contact.get('email', '') or '',
        status=Order.Status.PENDING,
        currency=trip.currency,
        created_by=user if (user is not None and user.is_authenticated) else None,
        promo_code=promo_code_obj,
    )

    # 7. створюємо квитки одним bulk_create щоб не запускати post_save сигнал
    # для кожного квитка окремо (інакше recalculate_total виконається N разів
    # замість одного). signals.recalc_order_total_on_save при bulk_create
    # не викликається - тому далі робимо recalculate_total вручну.
    ticket_objects = [
        Ticket(
            order=order,
            passenger_first_name=pd['first_name'],
            passenger_last_name=pd['last_name'],
            document_type=pd.get('document_type', Ticket.DocumentType.PASSPORT),
            document_number=pd['document_number'],
            price_type=pd.get('price_type', Ticket.PriceType.ADULT),
            seat_number=pd.get('seat_number', '') or '',
            boarding_stop=boarding_stop,
            alighting_stop=alighting_stop,
            price=trip.base_price,
            status=Ticket.Status.BOOKED,
        )
        for pd in passengers
    ]
    created_tickets = Ticket.objects.bulk_create(ticket_objects)
    # bulk_create не викликає save() на кожному квитку, тому ticket_number
    # лишається порожнім. Заповнюємо його одним апдейтом.
    from datetime import datetime
    year = datetime.now().year
    for t in created_tickets:
        if not t.ticket_number and t.pk:
            t.ticket_number = f'TK-{year}-{t.pk:06d}'
    Ticket.objects.bulk_update(
        [t for t in created_tickets if t.pk and t.ticket_number],
        ['ticket_number'],
    )
    # один перерахунок суми замість N
    order.recalculate_total()

    # 8. інкремент лічильника промокоду (під замком, без race condition).
    if promo_code_obj:
        promo_code_obj.times_used = promo_code_obj.times_used + 1
        promo_code_obj.save(update_fields=['times_used'])

    # 9. лояльність: оновлюємо суму і списуємо бали користувача.
    if use_loyalty_points > 0 and user is not None and user.is_authenticated:
        from django.conf import settings as django_settings
        order.refresh_from_db(fields=['total_price', 'discount_amount'])
        available_points = max(0, int(user.loyalty_points or 0))
        max_redeem_ratio = getattr(django_settings, 'LOYALTY_MAX_REDEEM_RATIO', Decimal('0.5'))
        max_redeem = int(order.total_price * max_redeem_ratio)
        used = min(use_loyalty_points, available_points, max_redeem)
        if used > 0:
            order.discount_amount = (order.discount_amount or Decimal('0')) + Decimal(used)
            order.total_price = order.total_price - Decimal(used)
            order.save(update_fields=['discount_amount', 'total_price', 'updated_at'])
            # перечитуємо користувача під замком, щоб не списати двічі.
            locked_user = User.objects.select_for_update().get(pk=user.pk)
            locked_user.loyalty_points = max(0, (locked_user.loyalty_points or 0) - used)
            locked_user.save(update_fields=['loyalty_points'])
            # синхронізуємо у пам'яті теж.
            user.loyalty_points = locked_user.loyalty_points

    return order
