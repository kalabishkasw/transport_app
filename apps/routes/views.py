from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Route


@login_required
def route_map(request, route_id):
    """
    Сторінка з картою маршруту: всі зупинки як маркери,
    послідовно з'єднані лінією руху.
    """
    route = get_object_or_404(Route, pk=route_id)
    stops = list(route.stops.all().order_by('order'))

    stops_data = [
        {
            'order': s.order,
            'city': s.city,
            'country': s.country,
            'station': s.station_name or '',
            'address': s.address or '',
            'lat': float(s.latitude) if s.latitude is not None else None,
            'lng': float(s.longitude) if s.longitude is not None else None,
            'arrival': s.arrival_offset_minutes,
            'departure': s.departure_offset_minutes,
            'can_board': s.can_board,
            'can_alight': s.can_alight,
        }
        for s in stops
    ]
    has_coords = [s for s in stops_data if s['lat'] is not None and s['lng'] is not None]

    return render(request, 'routes/route_map.html', {
        'active_page': 'routes',
        'route': route,
        'stops': stops_data,
        'stops_with_coords': has_coords,
    })
