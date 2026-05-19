"""
views для віддачі pdf-документів.
ticket_pdf - квиток конкретного пасажира (доступ: власник або персонал).
passenger_list_pdf - посадковий лист рейсу (доступ: тільки персонал/водій).
сама генерація pdf лежить у services.py.
"""
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from apps.orders.models import Ticket
from apps.routes.models import Trip

from .services import generate_passenger_list_pdf, generate_ticket_pdf


def _user_can_view_ticket(user, ticket):
    """
    PDF квитка може дивитись:
    - персонал (адміністратор, диспетчер, бухгалтер) - усі квитки
    - клієнт-власник: створив замовлення сам або email збігається з контактним
    """
    if user.is_staff or getattr(user, 'role', None) in ('admin', 'dispatcher', 'accountant'):
        return True
    order = ticket.order
    if order.created_by_id == user.id:
        return True
    if order.contact_email and user.email and order.contact_email.lower() == user.email.lower():
        return True
    return False


@login_required
def ticket_pdf(request, ticket_id):
    """завантажити PDF квитка. тільки власник або працівник.
    мова PDF береться з сесії portal_lang (uk/en)."""
    ticket = get_object_or_404(
        Ticket.objects.select_related('order', 'order__trip__route', 'order__trip__vehicle'),
        pk=ticket_id,
    )
    if not _user_can_view_ticket(request.user, ticket):
        raise Http404('Квиток не знайдено.')
    lang = request.session.get('portal_lang', 'uk')
    pdf = generate_ticket_pdf(ticket, lang=lang)
    response = HttpResponse(pdf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="ticket_{ticket.ticket_number}.pdf"'
    return response


@login_required
def passenger_list_pdf(request, trip_id):
    """
    завантажити PDF посадкового листа.
    це службовий документ, доступний лише диспетчеру/адміну/водієві.
    """
    user = request.user
    if not (user.is_staff or getattr(user, 'role', None) in ('admin', 'dispatcher', 'driver')):
        raise Http404('Документ недоступний.')
    trip = get_object_or_404(Trip, pk=trip_id)
    lang = request.session.get('portal_lang', 'uk')
    pdf = generate_passenger_list_pdf(trip, lang=lang)
    response = HttpResponse(pdf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="passenger_list_trip_{trip.id}.pdf"'
    return response
