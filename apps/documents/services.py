"""
Сервіс генерації PDF-документів: квитків та посадкових листів.
Використовує ReportLab. Шрифт DejaVu Sans автоматично завантажується
у static/fonts/ при першому виклику.
"""

import platform
from io import BytesIO
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _get_system_font_paths():
    """
    Повертає (regular, bold) шляхи до системних шрифтів з підтримкою кирилиці.
    На Windows використовуємо Arial. На Linux/Mac DejaVu Sans.
    """
    bundled_regular = Path(settings.BASE_DIR) / 'static' / 'fonts' / 'DejaVuSans.ttf'
    bundled_bold = Path(settings.BASE_DIR) / 'static' / 'fonts' / 'DejaVuSans-Bold.ttf'
    if bundled_regular.exists() and bundled_bold.exists():
        return bundled_regular, bundled_bold

    if platform.system() == 'Windows':
        regular = Path(r'C:/Windows/Fonts/arial.ttf')
        bold = Path(r'C:/Windows/Fonts/arialbd.ttf')
    else:
        regular = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        bold = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    return regular, bold


_fonts_registered = False


def _register_fonts():
    """Реєстрація шрифту з підтримкою кирилиці у ReportLab."""
    global _fonts_registered
    if _fonts_registered:
        return
    regular, bold = _get_system_font_paths()
    if not regular.exists() or not bold.exists():
        raise RuntimeError(
            f'Не знайдено шрифт з підтримкою кирилиці. '
            f'Очікував: {regular} та {bold}. '
            f'Поклади DejaVuSans.ttf та DejaVuSans-Bold.ttf у static/fonts/'
        )
    pdfmetrics.registerFont(TTFont('DejaVu', str(regular)))
    pdfmetrics.registerFont(TTFont('DejaVu-Bold', str(bold)))
    _fonts_registered = True


COMPANY_NAME = 'TransAuto Travel'
COMPANY_TAG = 'Міжнародні пасажирські перевезення'


def generate_ticket_pdf(ticket):
    """
    Генерація PDF квитка. Повертає BytesIO з PDF.
    """
    _register_fonts()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A5,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f'Ticket {ticket.ticket_number}',
    )

    title = ParagraphStyle('Title', fontName='DejaVu-Bold', fontSize=16, alignment=1, spaceAfter=4)
    subtitle = ParagraphStyle('Subtitle', fontName='DejaVu', fontSize=9, alignment=1, spaceAfter=10, textColor=colors.grey)
    number = ParagraphStyle('Number', fontName='DejaVu-Bold', fontSize=12, alignment=1, spaceAfter=10)
    footer = ParagraphStyle('Footer', fontName='DejaVu', fontSize=8, alignment=1, textColor=colors.grey)

    elements = [
        Paragraph(COMPANY_NAME, title),
        Paragraph(COMPANY_TAG, subtitle),
        Paragraph('КВИТОК', ParagraphStyle('TicketTitle', fontName='DejaVu-Bold', fontSize=14, alignment=1, spaceAfter=4)),
        Paragraph(f'№ {ticket.ticket_number}', number),
        Spacer(1, 4 * mm),
    ]

    trip = ticket.order.trip
    route = trip.route
    info = [
        ['Маршрут', route.name],
        ['Код', route.code],
        ['Відправлення', trip.departure_at.strftime('%d.%m.%Y о %H:%M')],
        ['Транспорт', f'{trip.vehicle.brand} {trip.vehicle.model} ({trip.vehicle.registration_number})'],
        ['Пасажир', ticket.passenger_full_name],
        ['Документ', f'{ticket.get_document_type_display()}, {ticket.document_number}'],
        ['Посадка', f'{ticket.boarding_stop.city} ({ticket.boarding_stop.station_name or "-"})'],
        ['Висадка', f'{ticket.alighting_stop.city} ({ticket.alighting_stop.station_name or "-"})'],
        ['Місце', ticket.seat_number or '-'],
        ['Тип квитка', ticket.get_price_type_display()],
        ['Ціна', f'{ticket.price} {trip.currency}'],
        ['Статус', ticket.get_status_display()],
    ]

    table = Table(info, colWidths=[4.5 * cm, 9.5 * cm])
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'DejaVu', 10),
        ('FONT', (0, 0), (0, -1), 'DejaVu-Bold', 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    elements.append(table)

    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        'Квиток дійсний при наявності документа, що посвідчує особу пасажира. '
        'У разі запізнення на посадку місце не зберігається.',
        footer,
    ))

    doc.build(elements)
    buf.seek(0)
    return buf


def generate_passenger_list_pdf(trip):
    """
    Генерація посадкового листа: список усіх квитків на рейс.
    """
    from apps.orders.models import Ticket  # імпорт всередині функції щоб уникнути циклічних залежностей

    _register_fonts()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f'Passenger list trip {trip.id}',
    )

    title_style = ParagraphStyle('Title', fontName='DejaVu-Bold', fontSize=14, alignment=1, spaceAfter=10)
    subtitle = ParagraphStyle('Subtitle', fontName='DejaVu', fontSize=9, alignment=1, textColor=colors.grey, spaceAfter=10)
    info_style = ParagraphStyle('Info', fontName='DejaVu', fontSize=10, leading=14)

    elements = [
        Paragraph(COMPANY_NAME, ParagraphStyle('Co', fontName='DejaVu-Bold', fontSize=12, alignment=1, spaceAfter=2)),
        Paragraph(COMPANY_TAG, subtitle),
        Paragraph('ПОСАДКОВИЙ ЛИСТ ПАСАЖИРІВ', title_style),
    ]

    elements.append(Paragraph(f'<b>Маршрут:</b> {trip.route.name} ({trip.route.code})', info_style))
    elements.append(Paragraph(f'<b>Відправлення:</b> {trip.departure_at.strftime("%d.%m.%Y о %H:%M")}', info_style))
    elements.append(Paragraph(
        f'<b>Транспорт:</b> {trip.vehicle.brand} {trip.vehicle.model} ({trip.vehicle.registration_number})',
        info_style,
    ))
    co_part = f', змінний водій: {trip.co_driver}' if trip.co_driver_id else ''
    elements.append(Paragraph(f'<b>Водій:</b> {trip.main_driver}{co_part}', info_style))
    elements.append(Spacer(1, 5 * mm))

    tickets = Ticket.objects.filter(
        order__trip=trip,
        status__in=['booked', 'paid'],
    ).select_related('boarding_stop', 'alighting_stop').order_by(
        'passenger_last_name', 'passenger_first_name'
    )

    headers = ['№', 'Прізвище та ім\'я', 'Документ', 'Посадка', 'Висадка', 'Місце', 'Підпис']
    data = [headers]

    for i, t in enumerate(tickets, 1):
        data.append([
            str(i),
            t.passenger_full_name,
            f'{t.get_document_type_display()}: {t.document_number}',
            t.boarding_stop.city,
            t.alighting_stop.city,
            t.seat_number or '-',
            '',
        ])

    if len(data) == 1:
        data.append(['', 'На цей рейс ще немає квитків', '', '', '', '', ''])

    table = Table(data, colWidths=[1 * cm, 4.5 * cm, 4 * cm, 2.5 * cm, 2.5 * cm, 1.5 * cm, 3 * cm])
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'DejaVu', 9),
        ('FONT', (0, 0), (-1, 0), 'DejaVu-Bold', 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e7ff')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)

    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph(f'<b>Усього пасажирів:</b> {tickets.count()}', info_style))
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        'Підпис водія: ____________________ Дата: ____________________',
        ParagraphStyle('Sign', fontName='DejaVu', fontSize=10),
    ))

    doc.build(elements)
    buf.seek(0)
    return buf
