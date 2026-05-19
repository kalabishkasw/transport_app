"""
сервіс генерації pdf-документів: квитків і посадкових листів.
використовую reportlab. шрифт DejaVu Sans автоматично береться
з static/fonts/ при першому виклику.
"""

import platform
from io import BytesIO
from pathlib import Path

import qrcode
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _make_qr_image(data, size_cm=3):
    """згенерувати QR-код як ReportLab Image для вбудовування у PDF."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Image(buf, width=size_cm * cm, height=size_cm * cm)


def _get_system_font_paths():
    """
    повертає (regular, bold) шляхи до системних шрифтів з підтримкою кирилиці.
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
    """реєстрація шрифту з підтримкою кирилиці у ReportLab."""
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

# тексти на PDF-документах, окремо для UA і EN
PDF_LABELS = {
    'uk': {
        'tag': 'Міжнародні пасажирські перевезення',
        'ticket': 'КВИТОК',
        'route': 'Маршрут',
        'code': 'Код',
        'departure': 'Відправлення',
        'ticket_type': 'Тип квитка',
        'vehicle': 'Транспорт',
        'seat': 'Місце',
        'passenger': 'Пасажир',
        'document': 'Документ',
        'boarding': 'Посадка',
        'alighting': 'Висадка',
        'price': 'Ціна',
        'status': 'Статус',
        'scan_at_boarding': 'Скануй на посадці',
        'footer': (
            'Квиток дійсний при наявності документа, що посвідчує особу пасажира. '
            'У разі запізнення на посадку місце не зберігається. '
            'TransAuto Travel · support@transauto.travel'
        ),
        # посадковий лист
        'passenger_list_title': 'ПОСАДКОВИЙ ЛИСТ ПАСАЖИРІВ',
        'pl_route': 'Маршрут',
        'pl_departure': 'Відправлення',
        'pl_vehicle': 'Транспорт',
        'pl_driver': 'Водій',
        'pl_co_driver': 'змінний водій',
        'pl_n': '№',
        'pl_passenger': 'Прізвище та імя',
        'pl_document': 'Документ',
        'pl_boarding': 'Посадка',
        'pl_alighting': 'Висадка',
        'pl_seat': 'Місце',
        'pl_signature': 'Підпис',
        'pl_total': 'Усього пасажирів',
        'pl_no_tickets': 'На цей рейс ще немає квитків',
        'pl_driver_signature': 'Підпис водія: ____________________ Дата: ____________________',
    },
    'en': {
        'tag': 'International passenger transport',
        'ticket': 'TICKET',
        'route': 'Route',
        'code': 'Code',
        'departure': 'Departure',
        'ticket_type': 'Ticket type',
        'vehicle': 'Vehicle',
        'seat': 'Seat',
        'passenger': 'Passenger',
        'document': 'Document',
        'boarding': 'Boarding',
        'alighting': 'Drop-off',
        'price': 'Price',
        'status': 'Status',
        'scan_at_boarding': 'Scan at boarding',
        'footer': (
            'The ticket is valid only with an ID document. If you miss boarding, '
            'the seat is not reserved. '
            'TransAuto Travel · support@transauto.travel'
        ),
        # посадковий лист
        'passenger_list_title': 'PASSENGER BOARDING LIST',
        'pl_route': 'Route',
        'pl_departure': 'Departure',
        'pl_vehicle': 'Vehicle',
        'pl_driver': 'Driver',
        'pl_co_driver': 'co-driver',
        'pl_n': 'No',
        'pl_passenger': 'Last and first name',
        'pl_document': 'Document',
        'pl_boarding': 'Boarding',
        'pl_alighting': 'Drop-off',
        'pl_seat': 'Seat',
        'pl_signature': 'Signature',
        'pl_total': 'Total passengers',
        'pl_no_tickets': 'No tickets for this trip yet',
        'pl_driver_signature': 'Driver signature: ____________________ Date: ____________________',
    },
}


def _pdf_labels(lang):
    """повертає словник підписів PDF за мовою. Fallback на українську."""
    return PDF_LABELS.get(lang, PDF_LABELS['uk'])


def generate_ticket_pdf(ticket, lang='uk'):
    """
    генерація PDF квитка у вигляді посадкового талона на A4.
    гарантовано вміщується на одну сторінку.
    мова (lang) керує підписами полів і значеннями вибору
    (тип документа, статус, місто посадки/висадки).
    """
    # локальний імпорт щоб уникнути циклічних залежностей
    from apps.portal.templatetags.i18n_extras import (
        CITY_NAMES_EN, DOC_TYPE_EN, PRICE_TYPE_EN, TICKET_STATUS_EN,
        get_eur_to_uah,
    )
    from decimal import Decimal as _D
    L = _pdf_labels(lang)

    def tr_city(name):
        if lang == 'en' and name:
            return CITY_NAMES_EN.get(name, name)
        return name

    def tr_doc(value):
        if lang == 'en':
            return DOC_TYPE_EN.get(value, ticket.get_document_type_display())
        return ticket.get_document_type_display()

    def tr_price(value):
        if lang == 'en':
            return PRICE_TYPE_EN.get(value, ticket.get_price_type_display())
        return ticket.get_price_type_display()

    def tr_status(value):
        if lang == 'en':
            return TICKET_STATUS_EN.get(value, ticket.get_status_display())
        return ticket.get_status_display()

    def format_money(amount):
        """форматує суму у локальній валюті: UA - грн, EN - EUR."""
        if lang == 'en':
            return f'{_D(amount):.0f} EUR'
        rate = get_eur_to_uah()
        return f'{(_D(amount) * rate):.0f} грн'

    _register_fonts()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f'Ticket {ticket.ticket_number}',
    )

    # тут важливо: leading має бути >= fontSize, інакше у комірках таблиці тексти
    # сусідніх параграфів накладаються один на одного.
    co_title = ParagraphStyle('CoTitle', fontName='DejaVu-Bold', fontSize=18, leading=22, alignment=0, textColor=colors.HexColor('#0369a1'), spaceAfter=4)
    co_sub = ParagraphStyle('CoSub', fontName='DejaVu', fontSize=9, leading=12, alignment=0, textColor=colors.grey)
    title_big = ParagraphStyle('TitleBig', fontName='DejaVu-Bold', fontSize=22, leading=26, alignment=2, spaceAfter=6)
    number_style = ParagraphStyle('Num', fontName='DejaVu-Bold', fontSize=13, leading=16, alignment=2, textColor=colors.HexColor('#0369a1'), spaceAfter=2)
    footer_style = ParagraphStyle('Foot', fontName='DejaVu', fontSize=8, leading=11, alignment=1, textColor=colors.grey)
    cell_label = ParagraphStyle('Lbl', fontName='DejaVu', fontSize=8, leading=10, textColor=colors.HexColor('#64748b'), spaceAfter=2)
    cell_value = ParagraphStyle('Val', fontName='DejaVu-Bold', fontSize=11, leading=14, wordWrap='CJK')
    cell_value_sub = ParagraphStyle('ValSub', fontName='DejaVu', fontSize=8, leading=10, textColor=colors.HexColor('#475569'), wordWrap='CJK', spaceBefore=1)
    qr_caption = ParagraphStyle('QrCap', fontName='DejaVu', fontSize=8, leading=10, alignment=1, textColor=colors.grey, spaceBefore=4)

    elements = []

    trip = ticket.order.trip
    route = trip.route

    # шапка: лого ліворуч, № квитка праворуч
    header_data = [[
        [Paragraph(COMPANY_NAME, co_title), Paragraph(L['tag'], co_sub)],
        [Paragraph(L['ticket'], title_big), Paragraph(f'№ {ticket.ticket_number}', number_style)],
    ]]
    header = Table(header_data, colWidths=[10 * cm, 7 * cm])
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 4 * mm))

    # розділова лінія
    line = Table([[' ']], colWidths=[17 * cm], rowHeights=[1])
    line.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.HexColor('#4f46e5')),
    ]))
    elements.append(line)
    elements.append(Spacer(1, 6 * mm))

    # основна частина: інфо ліворуч (12 см), QR праворуч (5 см)
    qr_data = f'TICKET:{ticket.ticket_number}|TRIP:{trip.id}|DATE:{trip.departure_at:%Y-%m-%d}'
    qr_img = _make_qr_image(qr_data, size_cm=4.5)

    def field_cell(label, value, sub=None):
        """
        одна клітинка з лейблом (сірий) над значенням (жирним).
        якщо sub задано, додаємо ще третій рядок меншим сірим шрифтом
        (наприклад, назва автостанції під назвою міста).
        """
        items = [
            Paragraph(label, cell_label),
            Paragraph(str(value), cell_value),
        ]
        if sub:
            items.append(Paragraph(str(sub), cell_value_sub))
        return items

    # скорочення довгих назв транспорту, щоб не лізли на 3 рядки.
    vehicle_full = f'{trip.vehicle.brand} {trip.vehicle.model}'
    if len(vehicle_full) > 26:
        vehicle_full = f'{trip.vehicle.brand} {trip.vehicle.model[:22]}…'

    # кожен рядок таблиці = одна пара полів (зліва + спава). усього 6 рядків.
    route_name_localized = f'{tr_city(route.origin_city)} - {tr_city(route.destination_city)}'
    departure_str = trip.departure_at.strftime('%d.%m.%Y %H:%M')
    info_grid_data = [
        [field_cell(L['route'], route_name_localized),
         field_cell(L['code'], route.code)],
        [field_cell(L['departure'], departure_str),
         field_cell(L['ticket_type'], tr_price(ticket.price_type))],
        [field_cell(L['vehicle'], vehicle_full, sub=trip.vehicle.registration_number),
         field_cell(L['seat'], ticket.seat_number or '—')],
        [field_cell(L['passenger'], ticket.passenger_full_name),
         field_cell(L['document'], tr_doc(ticket.document_type), sub=ticket.document_number)],
        [field_cell(L['boarding'], tr_city(ticket.boarding_stop.city),
                    sub=ticket.boarding_stop.station_name or None),
         field_cell(L['alighting'], tr_city(ticket.alighting_stop.city),
                    sub=ticket.alighting_stop.station_name or None)],
        [field_cell(L['price'], format_money(ticket.price)),
         field_cell(L['status'], tr_status(ticket.status))],
    ]
    info_grid = Table(info_grid_data, colWidths=[6 * cm, 5.5 * cm])
    info_grid.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        # збільшені вертикальні відступи, щоб контент не налазив на роздільну лінію
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        # тонкі розділові лінії між парами
        ('LINEBELOW', (0, 0), (-1, -2), 0.3, colors.HexColor('#e2e8f0')),
    ]))

    qr_block_data = [[qr_img], [Paragraph(L['scan_at_boarding'], qr_caption)]]
    qr_block = Table(qr_block_data, colWidths=[5 * cm])
    qr_block.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    main_table = Table(
        [[info_grid, qr_block]],
        colWidths=[11.5 * cm, 5.5 * cm],
    )
    main_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (1, 0), (1, 0), 8),
    ]))
    elements.append(main_table)

    elements.append(Spacer(1, 12 * mm))

    # розділова лінія
    line2 = Table([[' ']], colWidths=[17 * cm], rowHeights=[1])
    line2.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    elements.append(line2)
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph(L['footer'], footer_style))

    doc.build(elements)
    buf.seek(0)
    return buf


def generate_passenger_list_pdf(trip, lang='uk'):
    """
    генерація посадкового листа: список усіх квитків на рейс.
    зазвичай це службовий документ для водія українською, але теж
    підтримуємо EN для повноти.
    """
    from apps.orders.models import Ticket  # імпорт всередині функції щоб уникнути циклічних залежностей
    from apps.portal.templatetags.i18n_extras import CITY_NAMES_EN

    L = _pdf_labels(lang)

    def tr_city(name):
        if lang == 'en' and name:
            return CITY_NAMES_EN.get(name, name)
        return name

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
        Paragraph(L['tag'], subtitle),
        Paragraph(L['passenger_list_title'], title_style),
    ]

    route_name_localized = f'{tr_city(trip.route.origin_city)} - {tr_city(trip.route.destination_city)}'
    elements.append(Paragraph(f'<b>{L["pl_route"]}:</b> {route_name_localized} ({trip.route.code})', info_style))
    elements.append(Paragraph(f'<b>{L["pl_departure"]}:</b> {trip.departure_at.strftime("%d.%m.%Y %H:%M")}', info_style))
    elements.append(Paragraph(
        f'<b>{L["pl_vehicle"]}:</b> {trip.vehicle.brand} {trip.vehicle.model} ({trip.vehicle.registration_number})',
        info_style,
    ))
    co_part = f', {L["pl_co_driver"]}: {trip.co_driver}' if trip.co_driver_id else ''
    elements.append(Paragraph(f'<b>{L["pl_driver"]}:</b> {trip.main_driver}{co_part}', info_style))
    elements.append(Spacer(1, 5 * mm))

    tickets = Ticket.objects.filter(
        order__trip=trip,
        status__in=['booked', 'paid', 'used'],
    ).select_related('boarding_stop', 'alighting_stop').order_by(
        'passenger_last_name', 'passenger_first_name'
    )

    cell_style = ParagraphStyle('Cell', fontName='DejaVu', fontSize=9, leading=11, wordWrap='CJK')
    cell_bold = ParagraphStyle('CellBold', fontName='DejaVu-Bold', fontSize=9, leading=11, wordWrap='CJK')

    DOC_SHORT_UA = {
        'passport': 'Паспорт',
        'id_card': 'ID-картка',
        'driving': 'Посв. водія',
        'birth': 'Свідоцтво',
    }
    DOC_SHORT_EN = {
        'passport': 'Passport',
        'id_card': 'ID card',
        'driving': 'Driving lic.',
        'birth': 'Birth cert.',
    }
    doc_short_map = DOC_SHORT_EN if lang == 'en' else DOC_SHORT_UA

    headers = [
        Paragraph(L['pl_n'], cell_bold),
        Paragraph(L['pl_passenger'], cell_bold),
        Paragraph(L['pl_document'], cell_bold),
        Paragraph(L['pl_boarding'], cell_bold),
        Paragraph(L['pl_alighting'], cell_bold),
        Paragraph(L['pl_seat'], cell_bold),
        Paragraph(L['pl_signature'], cell_bold),
    ]
    data = [headers]

    for i, t in enumerate(tickets, 1):
        doc_short = doc_short_map.get(t.document_type, t.get_document_type_display())
        data.append([
            Paragraph(str(i), cell_style),
            Paragraph(t.passenger_full_name, cell_style),
            Paragraph(f'{doc_short}: {t.document_number}', cell_style),
            Paragraph(tr_city(t.boarding_stop.city), cell_style),
            Paragraph(tr_city(t.alighting_stop.city), cell_style),
            Paragraph(t.seat_number or '-', cell_style),
            Paragraph('', cell_style),
        ])

    if len(data) == 1:
        data.append([
            Paragraph('', cell_style),
            Paragraph(L['pl_no_tickets'], cell_style),
            Paragraph('', cell_style),
            Paragraph('', cell_style),
            Paragraph('', cell_style),
            Paragraph('', cell_style),
            Paragraph('', cell_style),
        ])

    # ширини колонок (сума ~18 см, що поміщається у A4 з полями)
    table = Table(data, colWidths=[0.8 * cm, 4.2 * cm, 4.5 * cm, 2.3 * cm, 2.3 * cm, 1.4 * cm, 3 * cm])
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
    elements.append(Paragraph(f'<b>{L["pl_total"]}:</b> {tickets.count()}', info_style))
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        L['pl_driver_signature'],
        ParagraphStyle('Sign', fontName='DejaVu', fontSize=10),
    ))

    doc.build(elements)
    buf.seek(0)
    return buf
