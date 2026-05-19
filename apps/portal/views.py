"""
публічний кабінет клієнта: пошук рейсів, бронювання, особистий кабінет.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.orders.models import Order, Ticket
from apps.reviews.models import Review
from apps.routes.models import Stop, Trip

from .forms import (
    BookingContactForm,
    ClientRegisterForm,
    PassengerForm,
    ReviewForm,
    SearchForm,
)



# лендінг та пошук


COUNTRY_NAMES_UK = {
    'UA': 'Україна', 'PL': 'Польща', 'CZ': 'Чехія', 'SK': 'Словаччина',
    'HU': 'Угорщина', 'RO': 'Румунія', 'AT': 'Австрія', 'DE': 'Німеччина',
    'IT': 'Італія', 'FR': 'Франція', 'MD': 'Молдова', 'BG': 'Болгарія',
}
COUNTRY_NAMES_EN = {
    'UA': 'Ukraine', 'PL': 'Poland', 'CZ': 'Czech Republic', 'SK': 'Slovakia',
    'HU': 'Hungary', 'RO': 'Romania', 'AT': 'Austria', 'DE': 'Germany',
    'IT': 'Italy', 'FR': 'France', 'MD': 'Moldova', 'BG': 'Bulgaria',
}


def _pluralize_uk(n, one, few, many):
    """
    повертає правильну форму іменника для числа n за українськими правилами.
    приклад: _pluralize_uk(1, 'день', 'дні', 'днів') -> 'день'
             _pluralize_uk(3, 'день', 'дні', 'днів') -> 'дні'
             _pluralize_uk(5, 'день', 'дні', 'днів') -> 'днів'
    """
    n = abs(n)
    last_two = n % 100
    last = n % 10
    if 11 <= last_two <= 14:
        return many
    if last == 1:
        return one
    if 2 <= last <= 4:
        return few
    return many


CITIES_CACHE_TTL = 600  # 10 хвилин


def _all_cities():
    """
    унікальні назви всіх міст (для backward compat).
    кешуємо у memory-cache на 10 хв, щоб не довбати БД на кожен рендер головної.
    """
    cached = cache.get('portal_all_cities_v1')
    if cached is not None:
        return cached
    from apps.routes.models import Route, Stop
    cities = set()
    for r in Route.objects.values_list('origin_city', 'destination_city'):
        cities.update(c for c in r if c)
    cities.update(Stop.objects.values_list('city', flat=True))
    result = sorted(cities)
    cache.set('portal_all_cities_v1', result, CITIES_CACHE_TTL)
    return result


def _cities_with_country(lang='uk'):
    """
    список (city, country_code, country_name) для autocomplete.
    кешуємо окремо для кожної мови.
    """
    cache_key = f'portal_cities_with_country_v1_{lang}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    from apps.routes.models import Route, Stop
    seen = {}
    for r in Route.objects.values('origin_city', 'origin_country').distinct():
        if r['origin_city']:
            seen[r['origin_city']] = r['origin_country']
    for r in Route.objects.values('destination_city', 'destination_country').distinct():
        if r['destination_city']:
            seen.setdefault(r['destination_city'], r['destination_country'])
    for r in Stop.objects.values('city', 'country').distinct():
        if r['city']:
            seen.setdefault(r['city'], r['country'])
    names = COUNTRY_NAMES_EN if lang == 'en' else COUNTRY_NAMES_UK
    result = []
    for city in sorted(seen.keys()):
        code = seen[city] or ''
        result.append({
            'name': city,
            'country_code': code,
            'country_name': names.get(code, code),
        })
    cache.set(cache_key, result, CITIES_CACHE_TTL)
    return result


def home(request):
    """лендінг з пошуковою формою та найближчими рейсами."""
    from .i18n import get_translations
    today = timezone.now().date()
    popular_routes = (
        Trip.objects
        .filter(
            departure_at__date__gte=today,
            status__in=['on_sale', 'planned'],
        )
        .select_related('route', 'vehicle')
        .order_by('departure_at')[:6]
    )

    from apps.routes.models import Route
    from apps.customers.models import Customer

    stats = {
        'passengers_total': max(Ticket.objects.filter(status__in=['paid', 'used', 'booked']).count() * 17, 12500),
        'trips_per_month': Trip.objects.filter(departure_at__gte=timezone.now() - timedelta(days=30)).count() or 120,
        'routes_count': Route.objects.filter(is_active=True).count() or 25,
        'cities_count': len(_all_cities()) or 40,
    }

    # FAQ за поточною мовою
    lang = request.session.get('portal_lang', 'uk')
    t = get_translations(lang)
    faq_items = [
        (t['faq_q1'], t['faq_a1']),
        (t['faq_q2'], t['faq_a2']),
        (t['faq_q3'], t['faq_a3']),
        (t['faq_q4'], t['faq_a4']),
        (t['faq_q5'], t['faq_a5']),
    ]

    return render(request, 'portal/home.html', {
        'form': SearchForm(initial={'date': today}),
        'popular': popular_routes,
        'cities': _all_cities(),
        'cities_with_country': _cities_with_country(lang),
        'stats': stats,
        'faq_items': faq_items,
    })


def search(request):
    """пошук рейсів за містами та датою."""
    form = SearchForm(request.GET or None)
    trips = []
    searched = False
    cities = _all_cities()
    alternatives = {
        'nearby_dates': [],   # той самий маршрут на сусідні дати
        'same_destination': [],  # інші рейси у те саме місто
        'same_origin': [],    # інші напрями з того ж міста
    }

    if form.is_valid():
        searched = True
        origin = form.cleaned_data['origin'].strip()
        destination = form.cleaned_data['destination'].strip()
        search_date = form.cleaned_data.get('date')

        qs = (
            Trip.objects
            .select_related('route', 'vehicle', 'main_driver__user')
            .filter(status__in=['on_sale', 'planned'])
        )
        if origin:
            qs = qs.filter(
                Q(route__origin_city__icontains=origin) |
                Q(route__stops__city__icontains=origin)
            ).distinct()
        if destination:
            qs = qs.filter(
                Q(route__destination_city__icontains=destination) |
                Q(route__stops__city__icontains=destination)
            ).distinct()
        if search_date:
            qs = qs.filter(departure_at__date=search_date)
        else:
            qs = qs.filter(departure_at__gte=timezone.now())

        qs = qs.annotate(
            sold=Count(
                'orders__tickets',
                filter=Q(orders__tickets__status__in=['booked', 'paid']),
                distinct=True,
            )
        ).order_by('departure_at')

        trips = list(qs[:50])
        for t in trips:
            t.free = max(0, (t.vehicle.seats_total or 0) - t.sold)

        # якщо нічого не знайшли - готуємо альтернативи для користувача.
        if not trips:
            now = timezone.now()
            alt_qs = (
                Trip.objects
                .select_related('route', 'vehicle')
                .filter(status__in=['on_sale', 'planned'], departure_at__gte=now)
                .annotate(
                    sold=Count(
                        'orders__tickets',
                        filter=Q(orders__tickets__status__in=['booked', 'paid']),
                        distinct=True,
                    )
                )
            )

            # 1. той самий маршрут на дати ±7 днів від обраної.
            if origin and destination and search_date:
                date_min = search_date - timedelta(days=7)
                date_max = search_date + timedelta(days=7)
                nearby = (
                    alt_qs
                    .filter(
                        Q(route__origin_city__icontains=origin) |
                        Q(route__stops__city__icontains=origin)
                    )
                    .filter(
                        Q(route__destination_city__icontains=destination) |
                        Q(route__stops__city__icontains=destination)
                    )
                    .filter(departure_at__date__gte=date_min, departure_at__date__lte=date_max)
                    .exclude(departure_at__date=search_date)
                    .order_by('departure_at')
                    .distinct()[:6]
                )
                alternatives['nearby_dates'] = list(nearby)
                for t in alternatives['nearby_dates']:
                    t.free = max(0, (t.vehicle.seats_total or 0) - t.sold)

            # 2. інші рейси у той самий пункт призначення (з інших міст).
            if destination:
                same_dest = (
                    alt_qs
                    .filter(
                        Q(route__destination_city__icontains=destination) |
                        Q(route__stops__city__icontains=destination)
                    )
                    .order_by('departure_at')
                    .distinct()[:4]
                )
                alternatives['same_destination'] = list(same_dest)
                for t in alternatives['same_destination']:
                    t.free = max(0, (t.vehicle.seats_total or 0) - t.sold)

            # 3. інші напрями з того ж міста відправлення.
            if origin:
                same_orig = (
                    alt_qs
                    .filter(
                        Q(route__origin_city__icontains=origin) |
                        Q(route__stops__city__icontains=origin)
                    )
                    .order_by('departure_at')
                    .distinct()[:4]
                )
                alternatives['same_origin'] = list(same_orig)
                for t in alternatives['same_origin']:
                    t.free = max(0, (t.vehicle.seats_total or 0) - t.sold)

    lang = request.session.get('portal_lang', 'uk')
    return render(request, 'portal/search.html', {
        'form': form,
        'trips': trips,
        'searched': searched,
        'alternatives': alternatives,
        'searched_origin': form.cleaned_data.get('origin', '').strip() if form.is_valid() else '',
        'searched_destination': form.cleaned_data.get('destination', '').strip() if form.is_valid() else '',
        'searched_date': form.cleaned_data.get('date') if form.is_valid() else None,
        'cities': cities,
        'cities_with_country': _cities_with_country(lang),
    })



# деталі рейсу та бронювання


def trip_detail(request, trip_id):
    """публічна сторінка рейсу з картою та кнопкою купівлі."""
    from django.db.models import Avg
    trip = get_object_or_404(
        Trip.objects.select_related('route', 'vehicle', 'main_driver__user'),
        pk=trip_id,
    )
    if trip.status not in ('on_sale', 'planned'):
        raise Http404('Рейс недоступний для бронювання.')

    # відгуки про цей маршрут (по всіх рейсах цього маршруту)
    reviews_qs = Review.objects.filter(
        trip__route=trip.route,
        is_published=True,
    ).select_related('user', 'trip').order_by('-created_at')
    reviews = list(reviews_qs[:5])
    rating_stats = reviews_qs.aggregate(
        avg=Avg('rating'),
        count=Count('id'),
    )

    stops = list(trip.route.stops.all().order_by('order'))
    sold = Ticket.objects.filter(
        order__trip=trip,
        status__in=['booked', 'paid'],
    ).count()
    free = (trip.vehicle.seats_total or 0) - sold

    stops_data = [
        {
            'order': s.order,
            'city': s.city,
            'country': s.country,
            'station': s.station_name or '',
            'lat': float(s.latitude) if s.latitude is not None else None,
            'lng': float(s.longitude) if s.longitude is not None else None,
        }
        for s in stops
    ]
    stops_with_coords = [s for s in stops_data if s['lat'] is not None]

    return render(request, 'portal/trip_detail.html', {
        'trip': trip,
        'stops': stops,
        'free': free,
        'sold': sold,
        'stops_with_coords': stops_with_coords,
        'reviews': reviews,
        'rating_stats': rating_stats,
    })


def trip_track(request, trip_id):
    """
    сторінка відстеження рейсу у реальному часі.
    доступна для будь-якого активного або в дорозі рейсу.
    """
    import json
    trip = get_object_or_404(
        Trip.objects.select_related('route', 'vehicle', 'main_driver__user'),
        pk=trip_id,
    )
    if trip.status == 'cancelled':
        raise Http404('Рейс скасовано.')

    stops = list(trip.route.stops.all().order_by('order'))
    stops_with_coords = [
        {
            'order': s.order,
            'city': s.city,
            'country': s.country,
            'station': s.station_name or '',
            'lat': float(s.latitude) if s.latitude is not None else None,
            'lng': float(s.longitude) if s.longitude is not None else None,
            'departure_offset': s.departure_offset_minutes,
            'arrival_offset': s.arrival_offset_minutes,
        }
        for s in stops if s.latitude is not None
    ]

    return render(request, 'portal/trip_track.html', {
        'trip': trip,
        'stops': stops,
        'stops_with_coords_json': json.dumps(stops_with_coords),
    })


def trip_position_api(request, trip_id):
    """
    JSON API: повертає поточну псевдо-GPS позицію автобуса.
    Викликається з JavaScript кожні 5-10 секунд.

    параметр ?demo=1 запускає прискорену симуляцію (для демо рейсів,
    які заплановано на майбутнє).
    """
    from .gps_simulator import simulate_position

    trip = get_object_or_404(
        Trip.objects.select_related('route', 'vehicle'),
        pk=trip_id,
    )

    demo_mode = request.GET.get('demo') == '1'
    pos = simulate_position(trip, demo_mode=demo_mode)

    if pos is None:
        if trip.status == 'cancelled':
            return JsonResponse({
                'status': 'cancelled',
                'message': 'Рейс скасовано',
            })
        # немає координат у зупинок або рейс ще не почався.
        now = timezone.now()
        if trip.departure_at > now:
            total_minutes = int((trip.departure_at - now).total_seconds() / 60)
            # форматування у дні/години/хвилини для зручного читання
            days = total_minutes // (24 * 60)
            hours = (total_minutes % (24 * 60)) // 60
            minutes = total_minutes % 60
            parts = []
            if days > 0:
                parts.append(f'{days} {_pluralize_uk(days, "день", "дні", "днів")}')
            if hours > 0:
                parts.append(f'{hours} {_pluralize_uk(hours, "година", "години", "годин")}')
            if minutes > 0 or not parts:
                parts.append(f'{minutes} {_pluralize_uk(minutes, "хвилина", "хвилини", "хвилин")}')
            human = ' '.join(parts)
            return JsonResponse({
                'status': 'pending',
                'message': f'Рейс розпочнеться через {human} (увімкніть demo-режим, щоб побачити симуляцію руху)',
                'minutes_to_start': total_minutes,
                'departure_at': trip.departure_at.isoformat(),
            })
        return JsonResponse({
            'status': 'unavailable',
            'message': 'Маршрут не має координат зупинок',
        })

    return JsonResponse({
        'status': 'finished' if pos.is_finished else 'in_transit',
        'lat': pos.lat,
        'lng': pos.lng,
        'speed_kmh': pos.speed_kmh,
        'progress_percent': pos.progress_percent,
        'nearest_stop': pos.nearest_stop_name,
        'nearest_stop_index': pos.nearest_stop_index,
        'next_stop': pos.next_stop_name,
        'eta_minutes_to_next': pos.eta_minutes,
        'is_finished': pos.is_finished,
        'minutes_since_departure': pos.minutes_since_departure,
        'segment_t': pos.segment_t,
        'updated_at': timezone.now().isoformat(),
        'demo_mode': demo_mode,
    })


def booking_form(request, trip_id):
    """
    форма бронювання: контактні дані, кількість пасажирів, дані пасажирів.
    підтримує і анонімне, і авторизоване бронювання.
    """
    trip = get_object_or_404(
        Trip.objects.select_related('route', 'vehicle'),
        pk=trip_id,
    )
    if trip.status not in ('on_sale', 'planned'):
        messages.error(request, 'Рейс недоступний для бронювання.')
        return redirect('portal:home')

    occupied_tickets = Ticket.objects.filter(
        order__trip=trip,
        status__in=['booked', 'paid'],
    ).exclude(seat_number='').values_list('seat_number', flat=True)
    occupied_seats = list(occupied_tickets)
    sold = Ticket.objects.filter(
        order__trip=trip,
        status__in=['booked', 'paid'],
    ).count()
    free = max(0, (trip.vehicle.seats_total or 0) - sold)

    if free <= 0:
        messages.error(request, 'На цьому рейсі немає вільних місць.')
        return redirect('portal:trip_detail', trip_id=trip.id)

    stops = list(trip.route.stops.all().order_by('order'))
    boarding_options = [s for s in stops if s.can_board]
    alighting_options = [s for s in stops if s.can_alight]

    lang = request.session.get('portal_lang', 'uk')

    if request.method == 'POST':
        try:
            count = int(request.POST.get('count', '1'))
        except ValueError:
            count = 1
        count = max(1, min(count, free, 10))

        contact_form = BookingContactForm(request.POST)
        passenger_forms = [
            PassengerForm(request.POST, prefix=f'p{i}', lang=lang)
            for i in range(count)
        ]
        all_valid = contact_form.is_valid() and all(f.is_valid() for f in passenger_forms)

        # допоміжна функція щоб не дублювати рендер форми при помилках,
        # зберігаючи усі заповнені поля контакту і пасажирів
        def _render_form_with_errors():
            return render(request, 'portal/booking_form.html', {
                'trip': trip,
                'free': free,
                'count': count,
                'count_options': list(range(1, min(free, 10) + 1)),
                'contact_form': contact_form,
                'passenger_forms': passenger_forms,
                'boarding_options': boarding_options,
                'alighting_options': alighting_options,
                'total_price': trip.base_price * count,
                'occupied_seats': occupied_seats,
                'total_seats': trip.vehicle.seats_total or 0,
            })

        if all_valid:
            data = contact_form.cleaned_data
            try:
                boarding = Stop.objects.get(pk=data['boarding_stop'], route=trip.route)
                alighting = Stop.objects.get(pk=data['alighting_stop'], route=trip.route)
            except Stop.DoesNotExist:
                messages.error(request, 'Невірно обрано пункт посадки чи висадки.')
                return _render_form_with_errors()

            promo_input = (request.POST.get('promo_code') or '').strip().upper()
            use_points_input = 0
            if request.user.is_authenticated:
                try:
                    use_points_input = int(request.POST.get('use_points', '0'))
                except ValueError:
                    use_points_input = 0

            # уся бізнес-логіка створення замовлення в одній транзакції
            # з блокуванням рейсу та промокоду, щоб уникнути race condition.
            try:
                from .booking_service import create_booking, BookingError
                order = create_booking(
                    trip_id=trip.id,
                    contact=data,
                    passengers=[pf.cleaned_data for pf in passenger_forms],
                    boarding_stop=boarding,
                    alighting_stop=alighting,
                    user=request.user if request.user.is_authenticated else None,
                    promo_code_input=promo_input,
                    use_loyalty_points=use_points_input,
                )
            except BookingError as e:
                # помилка бізнес-логіки (немає місць, зайнятий seat, неправильні зупинки)
                # повертаємо форму з даними щоб користувач не вводив усе наново
                messages.error(request, str(e))
                return _render_form_with_errors()
            except Exception as e:
                import logging
                logging.getLogger(__name__).exception('Невідома помилка при бронюванні рейсу %s', trip.id)
                messages.error(request, f'Сталася технічна помилка: {e}. Спробуйте ще раз або звяжіться з підтримкою.')
                return _render_form_with_errors()

            # запамʼятовуємо id свіжого замовлення у сесії, щоб дати доступ
            # до booking_done навіть анонімному (незалогіненому) користувачу
            recent_ids = request.session.get('recent_booking_ids', [])
            recent_ids.append(order.id)
            request.session['recent_booking_ids'] = recent_ids[-10:]
            messages.success(request, 'Замовлення створено успішно.')
            return redirect('portal:booking_done', order_id=order.id)
    else:
        try:
            count = int(request.GET.get('count', '1'))
        except ValueError:
            count = 1
        count = max(1, min(count, free, 10))

        contact_initial = {}
        if request.user.is_authenticated:
            contact_initial = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone': getattr(request.user, 'phone', ''),
                'email': request.user.email,
            }

        contact_form = BookingContactForm(initial=contact_initial)
        passenger_forms = [PassengerForm(prefix=f'p{i}', lang=lang) for i in range(count)]

    return render(request, 'portal/booking_form.html', {
        'trip': trip,
        'free': free,
        'count': count,
        'count_options': list(range(1, min(free, 10) + 1)),
        'contact_form': contact_form,
        'passenger_forms': passenger_forms,
        'boarding_options': boarding_options,
        'alighting_options': alighting_options,
        'total_price': trip.base_price * count,
        'occupied_seats': occupied_seats,
        'total_seats': trip.vehicle.seats_total or 0,
    })


def booking_done(request, order_id):
    """
    сторінка підтвердження замовлення. Доступ дозволено staff,
    власнику замовлення, або тому хто щойно його створив (recent_booking_ids у сесії).
    Без перевірки був би IDOR - чужий міг би переглянути контакт і список пасажирів
    знаючи лише номер замовлення.
    """
    order = get_object_or_404(
        Order.objects.select_related('trip__route', 'trip__vehicle'),
        pk=order_id,
    )
    recent_ids = request.session.get('recent_booking_ids', [])
    has_access = (
        request.user.is_staff
        or _is_order_owner(request.user, order)
        or order.id in recent_ids
    )
    if not has_access:
        raise Http404('Замовлення не знайдено.')
    tickets = order.tickets.select_related('boarding_stop', 'alighting_stop').all()
    return render(request, 'portal/booking_done.html', {
        'order': order,
        'tickets': tickets,
    })



# Mock онлайн-оплата (псевдо-платіжний шлюз для демонстрації)


@login_required(login_url='/login/')
def payment_form(request, order_id):
    """
    сторінка псевдо-оплати: імітує платіжний шлюз типу LiqPay чи Fondy.
    доступ лише власнику замовлення або співробітнику.
    """
    order = get_object_or_404(
        Order.objects.select_related('trip__route', 'trip__vehicle'),
        pk=order_id,
    )
    if not _is_order_owner(request.user, order) and not request.user.is_staff:
        raise Http404('Замовлення не знайдено.')

    if order.status in (Order.Status.PAID, Order.Status.COMPLETED, Order.Status.CANCELLED, Order.Status.REFUNDED):
        messages.info(request, f'Замовлення вже у статусі "{order.get_status_display()}", оплата неможлива.')
        return redirect('portal:booking_done', order_id=order.id)

    return render(request, 'portal/payment_form.html', {
        'order': order,
    })


@login_required(login_url='/login/')
def payment_process(request, order_id):
    """
    POST-обробник псевдо-оплати. Перевіряє "номер картки" (мінімальна валідація),
    переводить замовлення у PAID, квитки у PAID, ставить paid_at = now.

    Це mock! Реальна інтеграція з LiqPay/Stripe потребує API-ключів, callback-URL,
    верифікації підпису, обробки webhook про результат платежу.
    """
    if request.method != 'POST':
        return redirect('portal:payment_form', order_id=order_id)

    order = get_object_or_404(
        Order.objects.select_related('trip__route'),
        pk=order_id,
    )
    if not _is_order_owner(request.user, order) and not request.user.is_staff:
        raise Http404('Замовлення не знайдено.')

    if order.status in (Order.Status.PAID, Order.Status.COMPLETED, Order.Status.CANCELLED, Order.Status.REFUNDED):
        messages.warning(request, 'Замовлення вже не можна оплатити.')
        return redirect('portal:booking_done', order_id=order.id)

    card_number = (request.POST.get('card_number') or '').replace(' ', '')
    card_cvv = (request.POST.get('card_cvv') or '').strip()
    card_expiry = (request.POST.get('card_expiry') or '').strip()
    card_holder = (request.POST.get('card_holder') or '').strip()

    # мінімальна валідація.
    errors = []
    if not card_number.isdigit() or not (13 <= len(card_number) <= 19):
        errors.append('Невірний номер картки.')
    if not card_cvv.isdigit() or not (3 <= len(card_cvv) <= 4):
        errors.append('Невірний CVV.')
    if not card_expiry or '/' not in card_expiry:
        errors.append('Невірний термін дії (формат MM/YY).')
    if not card_holder:
        errors.append('Введіть імя власника картки.')

    # "тестова картка-відмова": номер закінчується на 0000.
    if card_number.endswith('0000'):
        errors.append('Платіж відхилено банком (тестова картка для demo).')

    if errors:
        for e in errors:
            messages.error(request, e)
        return redirect('portal:payment_form', order_id=order.id)

    # успішна "оплата".
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if locked_order.status in (Order.Status.PAID, Order.Status.COMPLETED):
            return redirect('portal:booking_done', order_id=order.id)
        locked_order.status = Order.Status.PAID
        locked_order.payment_method = Order.PaymentMethod.ONLINE
        locked_order.paid_at = timezone.now()
        locked_order.save(update_fields=['status', 'payment_method', 'paid_at', 'updated_at'])
        Ticket.objects.filter(order=locked_order, status=Ticket.Status.BOOKED).update(
            status=Ticket.Status.PAID,
        )

    masked = '**** **** **** ' + card_number[-4:]
    messages.success(
        request,
        f'Оплату {order.total_price} {order.currency} карткою {masked} успішно проведено.',
    )
    return redirect('portal:booking_done', order_id=order.id)



# авторизація клієнта


def client_login(request):
    """вхід клієнта (за email)."""
    next_url = request.GET.get('next') or request.POST.get('next') or '/account/'
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is None:
            user = authenticate(request, username=username.lower(), password=password)
        if user is not None:
            login(request, user)
            # захист від open redirect: дозволяємо лише URL у межах нашого хосту.
            # startswith('/') не достатньо: '//evil.com' теж починається зі '/' але
            # це протокол-relative URL, що повертає на чужий домен.
            if url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('portal:account')
        error = 'Невірний email або пароль.'
    return render(request, 'portal/login.html', {'error': error, 'next': next_url})


def client_register(request):
    """реєстрація клієнта."""
    if request.method == 'POST':
        form = ClientRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Реєстрація успішна. Ласкаво просимо!')
            return redirect('portal:account')
    else:
        form = ClientRegisterForm()
    return render(request, 'portal/register.html', {'form': form})


@require_POST
def client_logout(request):
    """вихід тільки через POST. Інакше можна вилогувати з зовнішнього сайту
    через звичайний <img src="...logout/"> або <a href> (CSRF logout)."""
    logout(request)
    return redirect('portal:home')


def set_language(request, lang_code):
    """Перемикач мови порталу."""
    from .i18n import SUPPORTED_LANGUAGES
    if lang_code in dict(SUPPORTED_LANGUAGES):
        request.session['portal_lang'] = lang_code
    next_url = request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)



# особистий кабінет


@login_required(login_url='/login/')
def account(request):
    """Кабінет: майбутні та минулі бронювання."""
    now = timezone.now()
    user_filter = Q(created_by=request.user)
    if request.user.email:
        user_filter |= Q(contact_email__iexact=request.user.email)
    orders = (
        Order.objects
        .filter(user_filter)
        .select_related('trip__route', 'trip__vehicle')
        .annotate(tickets_total=Count('tickets'))
        .order_by('-trip__departure_at')
        .distinct()
    )

    upcoming = [o for o in orders if o.trip.departure_at >= now]
    past = [o for o in orders if o.trip.departure_at < now]

    return render(request, 'portal/account.html', {
        'upcoming': upcoming,
        'past': past,
    })


@login_required(login_url='/login/')
def booking_detail(request, order_id):
    """деталі замовлення для клієнта (тільки своє)."""
    base_qs = Order.objects.select_related('trip__route', 'trip__vehicle')
    if request.user.is_staff:
        # працівникам видно будь-яке замовлення.
        order = get_object_or_404(base_qs, pk=order_id)
    else:
        # клієнт бачить лише свої: або створив сам, або email збігається.
        owner_filter = Q(created_by=request.user)
        if request.user.email:
            owner_filter |= Q(contact_email__iexact=request.user.email)
        order = get_object_or_404(base_qs.filter(owner_filter), pk=order_id)

    tickets = order.tickets.select_related('boarding_stop', 'alighting_stop').all()
    can_cancel = _can_cancel_order(order)
    return render(request, 'portal/booking_detail.html', {
        'order': order,
        'tickets': tickets,
        'can_cancel': can_cancel,
    })


def _is_order_owner(user, order):
    """чи цей користувач є власником замовлення (створив або email збігається)."""
    if not user.is_authenticated:
        return False
    if order.created_by_id == user.id:
        return True
    if order.contact_email and user.email:
        return order.contact_email.lower() == user.email.lower()
    return False


def _user_orders_filter(user):
    """
    Q-обєкт для фільтрації замовлень, які може бачити користувач.
    Допускає: створені користувачем АБО з контактним email = email користувача.
    Використовується у списках замовлень в особистому кабінеті.
    """
    f = Q(created_by=user)
    if user.email:
        f |= Q(contact_email__iexact=user.email)
    return f


def _can_cancel_order(order):
    """скасування дозволено не пізніше ніж за 24 години до рейсу
    і лише для активних статусів."""
    if order.status in (
        Order.Status.CANCELLED, Order.Status.REFUNDED,
        Order.Status.COMPLETED, Order.Status.IN_PROGRESS,
    ):
        return False
    hours_until = (order.trip.departure_at - timezone.now()).total_seconds() / 3600
    return hours_until >= 24


@login_required(login_url='/login/')
def cancel_booking(request, order_id):
    """скасування замовлення клієнтом. POST-only."""
    if request.method != 'POST':
        return redirect('portal:booking_detail', order_id=order_id)

    base_qs = Order.objects.select_related('trip')
    if request.user.is_staff:
        order = get_object_or_404(base_qs, pk=order_id)
    else:
        owner_filter = Q(created_by=request.user)
        if request.user.email:
            owner_filter |= Q(contact_email__iexact=request.user.email)
        order = get_object_or_404(base_qs.filter(owner_filter), pk=order_id)

    if not _can_cancel_order(order):
        messages.error(
            request,
            'Скасувати замовлення вже не можна. Воно або вже завершене, '
            'або до відправлення менше 24 годин.',
        )
        return redirect('portal:booking_detail', order_id=order.id)

    # лочу order на час оновлення, щоб два паралельні запити (наприклад
    # подвійний клік або одночасне скасування з двох вкладок) не призводили
    # до некоректного стану
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if locked.status in (
            Order.Status.CANCELLED, Order.Status.REFUNDED,
            Order.Status.COMPLETED, Order.Status.IN_PROGRESS,
        ):
            messages.warning(request, 'Стан замовлення вже змінився, скасування неможливе.')
            return redirect('portal:booking_detail', order_id=order.id)
        locked.tickets.update(status=Ticket.Status.CANCELLED)
        locked.status = Order.Status.REFUNDED
        locked.save(update_fields=['status', 'updated_at'])

    messages.success(
        request,
        f'Замовлення {order.order_number} скасовано. '
        'Кошти буде повернуто протягом 5 робочих днів.',
    )
    return redirect('portal:account')



# відгуки та бонусна програма


@login_required(login_url='/login/')
def leave_review(request, order_id):
    """Залишити відгук про поїздку."""
    owner_filter = Q(created_by=request.user)
    if request.user.email:
        owner_filter |= Q(contact_email__iexact=request.user.email)
    order = get_object_or_404(
        Order.objects.select_related('trip__route').filter(owner_filter),
        pk=order_id,
    )
    if order.status not in (Order.Status.COMPLETED,):
        messages.warning(request, 'Залишити відгук можна тільки після завершення поїздки.')
        return redirect('portal:booking_detail', order_id=order.id)

    existing = Review.objects.filter(trip=order.trip, user=request.user).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing)
        if form.is_valid():
            review = form.save(commit=False)
            review.trip = order.trip
            review.user = request.user
            review.order = order
            review.save()
            messages.success(request, 'Дякуємо за відгук!')
            return redirect('portal:booking_detail', order_id=order.id)
    else:
        form = ReviewForm(instance=existing)

    return render(request, 'portal/leave_review.html', {
        'order': order,
        'form': form,
        'existing': existing,
    })


@login_required(login_url='/login/')
def loyalty(request):
    """сторінка бонусної програми у кабінеті клієнта."""
    user = request.user
    completed_orders = Order.objects.filter(
        created_by=user,
        status=Order.Status.COMPLETED,
    ).select_related('trip__route').order_by('-trip__departure_at')[:20]

    # прогрес до наступного рівня. Рівні задаються у settings.LOYALTY_LEVELS,
    # формат: [(name, min_points, color_hex), ...]
    from django.conf import settings as django_settings
    levels = [(name, threshold) for name, threshold, _ in django_settings.LOYALTY_LEVELS]
    next_level = None
    progress = 100
    for name, threshold in levels:
        if user.loyalty_points < threshold:
            next_level = (name, threshold)
            break
    if next_level:
        prev_threshold = next((t for n, t in reversed(levels) if t <= user.loyalty_points), 0)
        denom = next_level[1] - prev_threshold
        progress = int(((user.loyalty_points - prev_threshold) / denom) * 100) if denom else 0

    return render(request, 'portal/loyalty.html', {
        'completed_orders': completed_orders,
        'next_level': next_level,
        'progress': progress,
        'levels': levels,
    })
