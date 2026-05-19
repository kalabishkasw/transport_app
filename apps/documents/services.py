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
COMPANY_TAG = 'Міжнародні пасажирські перевезення'


def generate_ticket_pdf(ticket):
    """
    генерація PDF квитка у вигляді посадкового талона на A4.
    гарантовано вміщується на одну сторінку.
    """
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
        [Paragraph(COMPANY_NAME, co_title), Paragraph(COMPANY_TAG, co_sub)],
        [Paragraph('КВИТОК', title_big), Paragraph(f'№ {ticket.ticket_number}', number_style)],
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
    info_grid_data = [
        [field_cell('Маршрут', route.name),
         field_cell('Код', route.code)],
        [field_cell('Відправлення', trip.departure_at.strftime('%d.%m.%Y о %H:%M')),
         field_cell('Тип квитка', ticket.get_price_type_display())],
        [field_cell('Транспорт', vehicle_full, sub=trip.vehicle.registration_number),
         field_cell('Місце', ticket.seat_number or '—')],
        [field_cell('Пасажир', ticket.passenger_full_name),
         field_cell('Документ', ticket.get_document_type_display(), sub=ticket.document_number)],
        [field_cell('Посадка', ticket.boarding_stop.city,
                    sub=ticket.boarding_stop.station_name or None),
         field_cell('Висадка', ticket.alighting_stop.city,
                    sub=ticket.alighting_stop.station_name or None)],
        [field_cell('Ціна', f'{ticket.price} {trip.currency}'),
         field_cell('Статус', ticket.get_status_display())],
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

    qr_block_data = [[qr_img], [Paragraph('Скануй на посадці', qr_caption)]]
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

    elements.append(Paragraph(
        'Квиток дійсний при наявності документа, що посвідчує особу пасажира. '
        'У разі запізнення на посадку місце не зберігається. '
        'TransAuto Travel · support@transauto.travel',
        footer_style,
    ))

    doc.build(elements)
    buf.seek(0)
    return buf


def generate_passenger_list_pdf(trip):
    """
    генерація посадкового листа: список усіх квитків на рейс.
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
        status__in=['booked', 'paid', 'used'],
    ).select_related('boarding_stop', 'alighting_stop').order_by(
        'passenger_last_name', 'passenger_first_name'
    )

    cell_style = ParagraphStyle('Cell', fontName='DejaVu', fontSize=9, leading=11, wordWrap='CJK')
    cell_bold = ParagraphStyle('CellBold', fontName='DejaVu-Bold', fontSize=9, leading=11, wordWrap='CJK')

    DOC_SHORT = {
        'passport': 'Паспорт',
        'id_card': 'ID-картка',
        'driving': 'Посв. водія',
        'birth': 'Свідоцтво',
    }

    headers = [
        Paragraph('№', cell_bold),
        Paragraph('Прізвище та ім\'я', cell_bold),
        Paragraph('Документ', cell_bold),
        Paragraph('Посадка', cell_bold),
        Paragraph('Висадка', cell_bold),
        Paragraph('Місце', cell_bold),
        Paragraph('Підпис', cell_bold),
    ]
    data = [headers]

    for i, t in enumerate(tickets, 1):
        doc_short = DOC_SHORT.get(t.document_type, t.get_document_type_display())
        data.append([
            Paragraph(str(i), cell_style),
            Paragraph(t.passenger_full_name, cell_style),
            Paragraph(f'{doc_short}: {t.document_number}', cell_style),
            Paragraph(t.boarding_stop.city, cell_style),
            Paragraph(t.alighting_stop.city, cell_style),
            Paragraph(t.seat_number or '-', cell_style),
            Paragraph('', cell_style),
        ])

    if len(data) == 1:
        data.append([
            Paragraph('', cell_style),
            Paragraph('На цей рейс ще немає квитків', cell_style),
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
    elements.append(Paragraph(f'<b>Усього пасажирів:</b> {tickets.count()}', info_style))
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        'Підпис водія: ____________________ Дата: ____________________',
        ParagraphStyle('Sign', fontName='DejaVu', fontSize=10),
    ))

    doc.build(elements)
    buf.seek(0)
    return buf
