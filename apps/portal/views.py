"""
Публічний кабінет клієнта: пошук рейсів, бронювання, особистий кабінет.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.orders.models import Order, Ticket
from apps.routes.models import Stop, Trip

from .forms import (
    BookingContactForm,
    ClientRegisterForm,
    PassengerForm,
    SearchForm,
)


# ----------------------------------------------------------------------
# Лендінг та пошук
# ----------------------------------------------------------------------

def home(request):
    """Лендінг з пошуковою формою та найближчими рейсами."""
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
    return render(request, 'portal/home.html', {
        'form': SearchForm(initial={'date': today + timedelta(days=1)}),
        'popular': popular_routes,
    })


def search(request):
    """Пошук рейсів за містами та датою."""
    form = SearchForm(request.GET or None)
    trips = []
    searched = False

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
            )
        ).order_by('departure_at')

        trips = list(qs[:50])
        for t in trips:
            t.free = (t.vehicle.seats_total or 0) - t.sold

    return render(request, 'portal/search.html', {
        'form': form,
        'trips': trips,
        'searched': searched,
    })


# ----------------------------------------------------------------------
# Деталі рейсу та бронювання
# ----------------------------------------------------------------------

def trip_detail(request, trip_id):
    """Публічна сторінка рейсу з картою та кнопкою купівлі."""
    trip = get_object_or_404(
        Trip.objects.select_related('route', 'vehicle', 'main_driver__user'),
        pk=trip_id,
    )
    if trip.status not in ('on_sale', 'planned'):
        raise Http404('Рейс недоступний для бронювання.')

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
    })


def booking_form(request, trip_id):
    """
    Форма бронювання: контактні дані, кількість пасажирів, дані пасажирів.
    Підтримує і анонімне, і авторизоване бронювання.
    """
    trip = get_object_or_404(
        Trip.objects.select_related('route', 'vehicle'),
        pk=trip_id,
    )
    if trip.status not in ('on_sale', 'planned'):
        messages.error(request, 'Рейс недоступний для бронювання.')
        return redirect('portal:home')

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

    if request.method == 'POST':
        try:
            count = int(request.POST.get('count', '1'))
        except ValueError:
            count = 1
        count = max(1, min(count, free, 10))

        contact_form = BookingContactForm(request.POST)
        passenger_forms = [
            PassengerForm(request.POST, prefix=f'p{i}')
            for i in range(count)
        ]
        all_valid = contact_form.is_valid() and all(f.is_valid() for f in passenger_forms)

        if all_valid:
            data = contact_form.cleaned_data
            try:
                boarding = Stop.objects.get(pk=data['boarding_stop'], route=trip.route)
                alighting = Stop.objects.get(pk=data['alighting_stop'], route=trip.route)
            except Stop.DoesNotExist:
                messages.error(request, 'Невірно обрано пункт посадки чи висадки.')
                return redirect('portal:booking_form', trip_id=trip.id)

            with transaction.atomic():
                order = Order.objects.create(
                    trip=trip,
                    contact_first_name=data['first_name'],
                    contact_last_name=data['last_name'],
                    contact_phone=data['phone'],
                    contact_email=data.get('email', ''),
                    status=Order.Status.PENDING,
                    currency=trip.currency,
                    created_by=request.user if request.user.is_authenticated else None,
                )
                for pf in passenger_forms:
                    pd = pf.cleaned_data
                    Ticket.objects.create(
                        order=order,
                        passenger_first_name=pd['first_name'],
                        passenger_last_name=pd['last_name'],
                        document_type=pd['document_type'],
                        document_number=pd['document_number'],
                        price_type=pd['price_type'],
                        seat_number=pd.get('seat_number', ''),
                        boarding_stop=boarding,
                        alighting_stop=alighting,
                        price=trip.base_price,
                        status=Ticket.Status.BOOKED,
                    )

            messages.success(request, f'Замовлення створено успішно.')
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
        passenger_forms = [PassengerForm(prefix=f'p{i}') for i in range(count)]

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
    })


def booking_done(request, order_id):
    """Сторінка підтвердження замовлення."""
    order = get_object_or_404(
        Order.objects.select_related('trip__route', 'trip__vehicle'),
        pk=order_id,
    )
    tickets = order.tickets.select_related('boarding_stop', 'alighting_stop').all()
    return render(request, 'portal/booking_done.html', {
        'order': order,
        'tickets': tickets,
    })


# ----------------------------------------------------------------------
# Авторизація клієнта
# ----------------------------------------------------------------------

def client_login(request):
    """Вхід клієнта (за email)."""
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
            if next_url.startswith('/'):
                return redirect(next_url)
            return redirect('portal:account')
        error = 'Невірний email або пароль.'
    return render(request, 'portal/login.html', {'error': error, 'next': next_url})


def client_register(request):
    """Реєстрація клієнта."""
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


def client_logout(request):
    logout(request)
    return redirect('portal:home')


# ----------------------------------------------------------------------
# Особистий кабінет
# ----------------------------------------------------------------------

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
    """Деталі замовлення для клієнта (тільки своє)."""
    order = get_object_or_404(
        Order.objects.select_related('trip__route', 'trip__vehicle'),
        pk=order_id,
    )
    is_owner = (
        order.created_by_id == request.user.id
        or (
            order.contact_email
            and order.contact_email.lower() == (request.user.email or '').lower()
        )
    )
    if not is_owner and not request.user.is_staff:
        raise Http404('Замовлення не знайдено.')

    tickets = order.tickets.select_related('boarding_stop', 'alighting_stop').all()
    return render(request, 'portal/booking_detail.html', {
        'order': order,
        'tickets': tickets,
    })
