from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from apps.orders.models import Ticket
from apps.routes.models import Trip

from .services import generate_passenger_list_pdf, generate_ticket_pdf


@login_required
def ticket_pdf(request, ticket_id):
    """Завантажити PDF квитка."""
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    pdf = generate_ticket_pdf(ticket)
    response = HttpResponse(pdf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="ticket_{ticket.ticket_number}.pdf"'
    return response


@login_required
def passenger_list_pdf(request, trip_id):
    """Завантажити PDF посадкового листа."""
    trip = get_object_or_404(Trip, pk=trip_id)
    pdf = generate_passenger_list_pdf(trip)
    response = HttpResponse(pdf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="passenger_list_trip_{trip.id}.pdf"'
    return response
