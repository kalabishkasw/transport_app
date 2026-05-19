"""
кастомні фільтри для перекладу динамічних даних (з БД) на EN.

у мене власна i18n не через gettext - тому статичні рядки шаблонів беруться
з TRANSLATIONS dict, а от значення з БД (міста, статуси, типи документів,
відгуки) перекладаю через ці фільтри.

використання у шаблоні:
    {% load i18n_extras %}
    {{ trip.route.origin_city|tr_city:LANG }}
"""
from django import template

register = template.Library()


# назви міст: UA → EN. невідомі повертаються як є.
CITY_NAMES_EN = {
    'Ужгород': 'Uzhhorod',
    'Львів': 'Lviv',
    'Київ': 'Kyiv',
    'Одеса': 'Odesa',
    'Харків': 'Kharkiv',
    'Чернівці': 'Chernivtsi',
    'Івано-Франківськ': 'Ivano-Frankivsk',
    'Тернопіль': 'Ternopil',
    'Луцьк': 'Lutsk',
    'Рівне': 'Rivne',
    'Мукачево': 'Mukachevo',
    'Кишинів': 'Chișinău',
    'Бельці': 'Bălți',
    'Кошице': 'Košice',
    'Братислава': 'Bratislava',
    'Прешов': 'Prešov',
    'Прага': 'Prague',
    'Брно': 'Brno',
    'Острава': 'Ostrava',
    'Варшава': 'Warsaw',
    'Краків': 'Kraków',
    'Вроцлав': 'Wrocław',
    'Познань': 'Poznań',
    'Люблін': 'Lublin',
    'Жешув': 'Rzeszów',
    'Берлін': 'Berlin',
    'Мюнхен': 'Munich',
    'Дрезден': 'Dresden',
    'Будапешт': 'Budapest',
    'Дебрецен': 'Debrecen',
    'Відень': 'Vienna',
    'Зальцбург': 'Salzburg',
    'Грац': 'Graz',
    'Бухарест': 'Bucharest',
    'Софія': 'Sofia',
    'Загреб': 'Zagreb',
    'Любляна': 'Ljubljana',
    'Мілан': 'Milan',
    'Рим': 'Rome',
    'Венеція': 'Venice',
}


# статуси замовлень: внутрішнє значення (з Order.Status) → EN
ORDER_STATUS_EN = {
    'pending': 'Pending confirmation',
    'confirmed': 'Confirmed',
    'paid': 'Paid',
    'in_progress': 'Trip in progress',
    'completed': 'Completed',
    'cancelled': 'Cancelled',
    'refunded': 'Refunded',
}

# статуси рейсів: значення з Trip.Status → EN
TRIP_STATUS_EN = {
    'planned': 'Planned',
    'on_sale': 'On sale',
    'in_progress': 'In transit',
    'completed': 'Completed',
    'cancelled': 'Cancelled',
}

# статуси квитків
TICKET_STATUS_EN = {
    'booked': 'Booked',
    'paid': 'Paid',
    'used': 'Used',
    'cancelled': 'Cancelled',
    'refunded': 'Refunded',
}

# типи документів
DOC_TYPE_EN = {
    'passport': 'International passport',
    'id_card': 'ID card',
    'driving': "Driver's license",
    'birth': 'Birth certificate',
}

# типи квитків (тарифи)
PRICE_TYPE_EN = {
    'adult': 'Adult',
    'child': 'Child',
    'student': 'Student',
    'senior': 'Senior',
    'disabled': 'Disabled',
}

# способи оплати
PAYMENT_METHOD_EN = {
    'cash': 'Cash',
    'card': 'Card',
    'bank': 'Bank transfer',
    'online': 'Online',
}


# мапа заголовків відгуків з seed_reviews.py
REVIEW_TITLE_EN = {
    'Все на найвищому рівні': 'Top quality',
    'Чудова поїздка': 'Great trip',
    'Все сподобалось': 'Liked everything',
    'Без зауважень': 'No complaints',
    'Все організовано': 'Well organized',
    'Сучасний автобус': 'Modern bus',
    'Приємно здивовані': 'Pleasantly surprised',
    'Швидко та комфортно': 'Fast and comfortable',
    'Найкращий вибір': 'Best choice',
    'Дякую': 'Thank you',
    'Загалом непогано': 'Overall fine',
    'Так собі': 'So-so',
    'Звичайний рейс': 'Ordinary trip',
    'Можна краще': 'Could be better',
    'Запізнення': 'Delay',
    'Незручно': 'Uncomfortable',
}

# мапа коментарів з seed_reviews.py
REVIEW_COMMENT_EN = {
    'Дуже зручний автобус, водії ввічливі, відправлення вчасно. Рекомендую.':
        'Very comfortable bus, drivers are polite, departed on time. Recommended.',
    'Чисто, тепло, Wi-Fi працював всю дорогу. Місця м\'які, спинки відкидаються.':
        'Clean, warm, Wi-Fi worked the whole way. Soft reclining seats.',
    'Купив квиток онлайн за 5 хвилин. На посадці без черг. Прибули раніше графіка.':
        'Bought the ticket online in 5 minutes. No queues at boarding. Arrived ahead of schedule.',
    'Гарний сервіс, водії вели обережно, зупинки на каві були приємні. Поїдемо ще.':
        'Nice service, drivers drove carefully, coffee stops were pleasant. We will travel again.',
    'Перетин кордону зайняв мінімум часу, водій усе пояснив. Якісний рівень.':
        'Border crossing took minimal time, the driver explained everything. Quality service.',
    'Кондиціонер, USB, туалет — все працює. Завжди буду користуватись.':
        'Air conditioning, USB, restroom, everything works. Will use again.',
    'Очікували значно гірше за такою ціною, але все на висоті.':
        'We expected much worse at this price, but everything was great.',
    'Прибули за графіком. Багажне відділення велике, туди влізла велика сумка.':
        'Arrived on time. The luggage compartment is large, fit a big bag.',
    'Не перший раз їжджу цим маршрутом. Завжди стабільна якість.':
        'Not my first time on this route. Quality is always consistent.',
    'Душевно та з турботою. Водій навіть допоміг із багажем. Молодці!':
        'Warm and caring. The driver even helped with luggage. Well done!',
    'Поїздка була нормальною. Невеликі затримки на кордоні, але це не від компанії.':
        'The trip was fine. Small delays at the border, but not the company\'s fault.',
    'Все виконано. Очікував трохи більше комфорту за таку ціну.':
        'Everything done. I expected a bit more comfort for this price.',
    'Нічого не скажеш поганого, але і нічого видатного. Звичайний транспорт.':
        'Nothing bad to say but nothing outstanding either. Ordinary transport.',
    'Все добре, але кондиціонер дув занадто сильно. Бажано регулювати індивідуально.':
        'All good, but the air conditioning blew too strongly. Better if it were adjustable individually.',
    'Виїхали з затримкою 40 хвилин без пояснень. Не вистачило інформування.':
        'Departed 40 minutes late without explanations. Lacked communication.',
    'Місця близько, ноги затерпли. Для довгих рейсів треба автобуси з більшим простором.':
        'Seats are close together, legs went numb. Long trips need buses with more legroom.',
}


# фільтри для шаблонів. усі беруть значення і lang, повертають
# перекладене або сам value якщо невідомме.

@register.filter
def tr_city(value, lang='uk'):
    if lang == 'en' and value:
        return CITY_NAMES_EN.get(value, value)
    return value


@register.filter
def tr_order_status(value, lang='uk'):
    if lang == 'en' and value:
        return ORDER_STATUS_EN.get(value, value)
    return value


@register.filter
def tr_trip_status(value, lang='uk'):
    if lang == 'en' and value:
        return TRIP_STATUS_EN.get(value, value)
    return value


@register.filter
def tr_ticket_status(value, lang='uk'):
    if lang == 'en' and value:
        return TICKET_STATUS_EN.get(value, value)
    return value


@register.filter
def tr_doc_type(value, lang='uk'):
    if lang == 'en' and value:
        return DOC_TYPE_EN.get(value, value)
    return value


@register.filter
def tr_price_type(value, lang='uk'):
    if lang == 'en' and value:
        return PRICE_TYPE_EN.get(value, value)
    return value


@register.filter
def tr_payment_method(value, lang='uk'):
    if lang == 'en' and value:
        return PAYMENT_METHOD_EN.get(value, value)
    return value


@register.filter
def tr_review_title(value, lang='uk'):
    if lang == 'en' and value:
        return REVIEW_TITLE_EN.get(value, value)
    return value


@register.filter
def tr_review_comment(value, lang='uk'):
    if lang == 'en' and value:
        return REVIEW_COMMENT_EN.get(value, value)
    return value
