"""
Веб-інтерфейс диспетчера: дашборд, списки та деталі сутностей.
Усі сторінки потребують авторизації.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.customers.models import Customer
from apps.fleet.models import Driver, Vehicle
from apps.orders.models import Order, Ticket
from apps.routes.models import Route, Trip


PAGE_SIZE = 20


# ----------------------------------------------------------------------
# Дашборд
# ----------------------------------------------------------------------

@login_required
def dashboard(request):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ahead = now + timedelta(days=7)

    trips_this_month = Trip.objects.filter(departure_at__gte=month_start).count()
    trips_active_today = Trip.objects.filter(
        departure_at__gte=today_start,
        departure_at__lt=today_start + timedelta(days=1),
    ).count()

    tickets_this_month = Ticket.objects.filter(
        created_at__gte=month_start,
        status__in=['booked', 'paid', 'used'],
    ).count()

    revenue_this_month = Order.objects.filter(
        created_at__gte=month_start,
        status__in=['paid', 'in_progress', 'completed'],
    ).aggregate(total=Sum('total_price'))['total'] or Decimal('0')

    customers_count = Customer.objects.filter(is_active=True).count()
    vehicles_active = Vehicle.objects.filter(is_active=True).count()
    drivers_available = Driver.objects.filter(is_available=True).count()
    routes_active = Route.objects.filter(is_active=True).count()

    upcoming_trips = (
        Trip.objects
        .filter(departure_at__gte=now, departure_at__lte=week_ahead)
        .select_related('route', 'vehicle', 'main_driver__user')
        .annotate(tickets_count=Count(
            'orders__tickets',
            filter=Q(orders__tickets__status__in=['booked', 'paid']),
        ))
        .order_by('departure_at')[:8]
    )

    recent_orders = (
        Order.objects
        .select_related('trip__route', 'customer')
        .annotate(tickets_total=Count('tickets'))
        .order_by('-created_at')[:8]
    )

    return render(request, 'core/dashboard.html', {
        'active_page': 'dashboard',
        'metrics': {
            'trips_this_month': trips_this_month,
            'trips_active_today': trips_active_today,
            'tickets_this_month': tickets_this_month,
            'revenue_this_month': revenue_this_month,
            'customers_count': customers_count,
            'vehicles_active': vehicles_active,
            'drivers_available': drivers_available,
            'routes_active': routes_active,
        },
        'upcoming_trips': upcoming_trips,
        'recent_orders': recent_orders,
    })


# ----------------------------------------------------------------------
# Рейси
# ----------------------------------------------------------------------

@login_required
def trips_list(request):
    qs = (
        Trip.objects
        .select_related('route', 'vehicle', 'main_driver__user')
        .annotate(tickets_count=Count(
            'orders__tickets',
            filter=Q(orders__tickets__status__in=['booked', 'paid']),
        ))
        .order_by('-departure_at')
    )

    status = request.GET.get('status', '')
    route_id = request.GET.get('route', '')
    search = request.GET.get('q', '').strip()

    if status:
        qs = qs.filter(status=status)
    if route_id:
        qs = qs.filter(route_id=route_id)
    if search:
        qs = qs.filter(
            Q(route__name__icontains=search) |
            Q(route__code__icontains=search) |
            Q(vehicle__registration_number__icontains=search)
        )

    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'core/trips_list.html', {
        'active_page': 'trips',
        'page': page,
        'trips': page.object_list,
        'status_choices': Trip.Status.choices,
        'routes': Route.objects.filter(is_active=True).order_by('code'),
        'filters': {'status': status, 'route': route_id, 'q': search},
    })


@login_required
def trip_detail(request, trip_id):
    trip = get_object_or_404(
        Trip.objects.select_related(
            'route', 'vehicle', 'main_driver__user', 'co_driver__user'
        ),
        pk=trip_id,
    )
    stops = trip.route.stops.all().order_by('order')
    tickets = (
        Ticket.objects
        .filter(order__trip=trip)
        .select_related('order', 'boarding_stop', 'alighting_stop')
        .order_by('passenger_last_name', 'passenger_first_name')
    )
    revenue = sum(
        (t.price for t in tickets if t.status in ('booked', 'paid', 'used')),
        start=Decimal('0'),
    )
    sold = sum(1 for t in tickets if t.status in ('booked', 'paid'))
    free_seats = (trip.vehicle.seats_total or 0) - sold

    return render(request, 'core/trip_detail.html', {
        'active_page': 'trips',
        'trip': trip,
        'stops': stops,
        'tickets': tickets,
        'revenue': revenue,
        'sold': sold,
        'free_seats': free_seats,
    })


# ----------------------------------------------------------------------
# Замовлення
# ----------------------------------------------------------------------

@login_required
def orders_list(request):
    qs = (
        Order.objects
        .select_related('trip__route', 'customer', 'created_by')
        .annotate(tickets_total=Count('tickets'))
        .order_by('-created_at')
    )

    status = request.GET.get('status', '')
    search = request.GET.get('q', '').strip()

    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(
            Q(order_number__icontains=search) |
            Q(contact_first_name__icontains=search) |
            Q(contact_last_name__icontains=search) |
            Q(contact_phone__icontains=search) |
            Q(customer__name__icontains=search)
        )

    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'core/orders_list.html', {
        'active_page': 'orders',
        'page': page,
        'orders': page.object_list,
        'status_choices': Order.Status.choices,
        'filters': {'status': status, 'q': search},
    })


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related(
            'trip__route', 'trip__vehicle', 'customer', 'created_by'
        ),
        pk=order_id,
    )
    tickets = order.tickets.select_related('boarding_stop', 'alighting_stop').all()
    return render(request, 'core/order_detail.html', {
        'active_page': 'orders',
        'order': order,
        'tickets': tickets,
    })


# ----------------------------------------------------------------------
# Клієнти
# ----------------------------------------------------------------------

@login_required
def customers_list(request):
    qs = (
        Customer.objects
        .annotate(orders_count=Count('orders'))
        .order_by('name')
    )
    country = request.GET.get('country', '')
    search = request.GET.get('q', '').strip()
    if country:
        qs = qs.filter(country=country)
    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(legal_name__icontains=search) |
            Q(tax_number__icontains=search) |
            Q(contact_person__icontains=search)
        )
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/customers_list.html', {
        'active_page': 'customers',
        'page': page,
        'customers': page.object_list,
        'countries': Customer.Country.choices,
        'filters': {'country': country, 'q': search},
    })


# ----------------------------------------------------------------------
# Автопарк
# ----------------------------------------------------------------------

@login_required
def vehicles_list(request):
    qs = Vehicle.objects.order_by('vehicle_type', 'registration_number')
    vehicle_type = request.GET.get('type', '')
    is_active = request.GET.get('active', '')
    search = request.GET.get('q', '').strip()
    if vehicle_type:
        qs = qs.filter(vehicle_type=vehicle_type)
    if is_active in ('1', '0'):
        qs = qs.filter(is_active=(is_active == '1'))
    if search:
        qs = qs.filter(
            Q(registration_number__icontains=search) |
            Q(brand__icontains=search) |
            Q(model__icontains=search)
        )
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/vehicles_list.html', {
        'active_page': 'vehicles',
        'page': page,
        'vehicles': page.object_list,
        'types': Vehicle.VehicleType.choices,
        'filters': {'type': vehicle_type, 'active': is_active, 'q': search},
    })


# ----------------------------------------------------------------------
# Водії
# ----------------------------------------------------------------------

@login_required
def drivers_list(request):
    qs = Driver.objects.select_related('user').order_by(
        'user__last_name', 'user__first_name',
    )
    available = request.GET.get('available', '')
    search = request.GET.get('q', '').strip()
    if available in ('1', '0'):
        qs = qs.filter(is_available=(available == '1'))
    if search:
        qs = qs.filter(
            Q(user__last_name__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(license_number__icontains=search) |
            Q(license_categories__icontains=search)
        )
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/drivers_list.html', {
        'active_page': 'drivers',
        'page': page,
        'drivers': page.object_list,
        'filters': {'available': available, 'q': search},
    })


# ----------------------------------------------------------------------
# Маршрути
# ----------------------------------------------------------------------

@login_required
def routes_list(request):
    qs = (
        Route.objects
        .annotate(
            stops_count=Count('stops', distinct=True),
            trips_count=Count('trips', distinct=True),
        )
        .order_by('code')
    )
    is_active = request.GET.get('active', '')
    search = request.GET.get('q', '').strip()
    if is_active in ('1', '0'):
        qs = qs.filter(is_active=(is_active == '1'))
    if search:
        qs = qs.filter(
            Q(code__icontains=search) |
            Q(name__icontains=search) |
            Q(origin_city__icontains=search) |
            Q(destination_city__icontains=search)
        )
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/routes_list.html', {
        'active_page': 'routes',
        'page': page,
        'routes': page.object_list,
        'filters': {'active': is_active, 'q': search},
    })
