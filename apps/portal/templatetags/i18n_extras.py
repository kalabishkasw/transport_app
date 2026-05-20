"""
кастомні фільтри для перекладу динамічних даних (з БД) на EN.

у мене власна i18n не через gettext - тому статичні рядки шаблонів беруться
з TRANSLATIONS dict, а от значення з БД (міста, статуси, типи документів,
відгуки) перекладаю через ці фільтри.

використання у шаблоні:
    {% load i18n_extras %}
    {{ trip.route.origin_city|tr_city:LANG }}
"""
import json
import logging
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.request import urlopen
from socket import timeout as SocketTimeout

from django import template
from django.core.cache import cache

register = template.Library()
logger = logging.getLogger(__name__)


# курс конверсії: припускаємо що всі ціни у БД зберігаються у EUR.
# для UA відображення множимо на актуальний курс і показуємо у грн.
# для EN залишаємо як є (EUR).
EUR_TO_UAH_FALLBACK = Decimal('51.8')
NBU_EUR_URL = 'https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=EUR&json'
RATE_CACHE_KEY = 'nbu_eur_to_uah_v1'
RATE_CACHE_TTL = 60 * 60 * 24  # 24 години


def get_eur_to_uah():
    """
    повертає актуальний курс EUR -> UAH.

    логіка:
    1. якщо у settings/env задано EUR_TO_UAH_FIXED - використовую його
       (для дипломної демонстрації стабільності цін незалежно від рестартів).
    2. інакше - беру з кешу.
    3. інакше - тягну з НБУ.
    4. fallback - EUR_TO_UAH_FALLBACK.

    при будь-якій помилці (нема інтернету, NBU не відповідає, формат не той)
    повертає fallback значення.
    """
    # фіксований курс з settings/env має пріоритет. так гарантую що для одного
    # рейсу ціна показується однаково на сторінці деталей і у формі бронювання,
    # навіть якщо між запитами кеш очистився чи runserver перезавантажився.
    from django.conf import settings as django_settings
    fixed = getattr(django_settings, 'EUR_TO_UAH_FIXED', '') or ''
    if fixed:
        try:
            return Decimal(str(fixed))
        except (InvalidOperation, ValueError, TypeError):
            pass

    cached = cache.get(RATE_CACHE_KEY)
    if cached is not None:
        try:
            return Decimal(str(cached))
        except (InvalidOperation, ValueError, TypeError):
            pass

    # перелічую конкретні очікувані помилки замість сирого Exception:
    # URLError - мережеві проблеми, SocketTimeout - таймаут,
    # JSONDecodeError - НБУ повернув не JSON, InvalidOperation/KeyError -
    # формат відповіді змінився.
    try:
        with urlopen(NBU_EUR_URL, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data and isinstance(data, list) and 'rate' in data[0]:
            rate = Decimal(str(data[0]['rate']))
            cache.set(RATE_CACHE_KEY, str(rate), RATE_CACHE_TTL)
            return rate
    except (URLError, SocketTimeout, json.JSONDecodeError,
            InvalidOperation, KeyError, IndexError, ValueError) as exc:
        logger.warning(
            'Не вдалося отримати курс НБУ (%s), використовую fallback %s',
            exc.__class__.__name__, EUR_TO_UAH_FALLBACK,
        )

    # кешую fallback на 1 годину щоб у разі довгих проблем з NBU
    # не довбати їх на кожен запит
    cache.set(RATE_CACHE_KEY, str(EUR_TO_UAH_FALLBACK), 60 * 60)
    return EUR_TO_UAH_FALLBACK


# назви міст: UA → EN. невідомі повертаються як є.
CITY_NAMES_EN = {
    # Україна
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
    'Чоп': 'Chop',
    'Дніпро': 'Dnipro',
    'Житомир': 'Zhytomyr',
    'Вінниця': 'Vinnytsia',
    'Хмельницький': 'Khmelnytskyi',
    'Запоріжжя': 'Zaporizhzhia',
    'Полтава': 'Poltava',
    'Суми': 'Sumy',
    # Молдова
    'Кишинів': 'Chișinău',
    'Бельці': 'Bălți',
    # Словаччина
    'Кошице': 'Košice',
    'Братислава': 'Bratislava',
    'Прешов': 'Prešov',
    'Жиліна': 'Žilina',
    'Тренчин': 'Trenčín',
    'Нітра': 'Nitra',
    'Банська Бистриця': 'Banská Bystrica',
    # Чехія
    'Прага': 'Prague',
    'Брно': 'Brno',
    'Острава': 'Ostrava',
    'Пльзень': 'Plzeň',
    # Польща
    'Варшава': 'Warsaw',
    'Краків': 'Kraków',
    'Вроцлав': 'Wrocław',
    'Познань': 'Poznań',
    'Люблін': 'Lublin',
    'Жешув': 'Rzeszów',
    'Гданськ': 'Gdańsk',
    'Катовиці': 'Katowice',
    # Німеччина
    'Берлін': 'Berlin',
    'Мюнхен': 'Munich',
    'Дрезден': 'Dresden',
    'Гамбург': 'Hamburg',
    'Франкфурт': 'Frankfurt',
    'Кельн': 'Cologne',
    # Угорщина
    'Будапешт': 'Budapest',
    'Дебрецен': 'Debrecen',
    'Сегед': 'Szeged',
    'Мішкольц': 'Miskolc',
    'Захонь': 'Záhony',
    # Австрія
    'Відень': 'Vienna',
    'Зальцбург': 'Salzburg',
    'Грац': 'Graz',
    'Лінц': 'Linz',
    # Румунія
    'Бухарест': 'Bucharest',
    'Сучава': 'Suceava',
    'Брашов': 'Brașov',
    'Клуж-Напока': 'Cluj-Napoca',
    'Тімішоара': 'Timișoara',
    'Ясси': 'Iași',
    # Інші
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


@register.filter
def price_local(amount, lang='uk'):
    """
    форматує ціну з конверсією за мовою.
    припускаю що amount у БД зберігається у EUR (базова валюта).
    UA: множу на актуальний курс НБУ і показую у грн (без копійок).
    EN: показую у EUR (без копійок).
    """
    if amount is None or amount == '':
        return ''
    try:
        amount = Decimal(str(amount))
    except (TypeError, ValueError):
        return str(amount)
    if lang == 'en':
        return f'{amount:.0f} EUR'
    rate = get_eur_to_uah()
    uah = (amount * rate).quantize(Decimal('1'))
    return f'{uah:.0f} грн'


@register.filter
def price_local_2(amount, lang='uk'):
    """так само як price_local але з 2 знаками після коми (для знижок)."""
    if amount is None or amount == '':
        return ''
    try:
        amount = Decimal(str(amount))
    except (TypeError, ValueError):
        return str(amount)
    if lang == 'en':
        return f'{amount:.2f} EUR'
    rate = get_eur_to_uah()
    uah = (amount * rate).quantize(Decimal('0.01'))
    return f'{uah:.2f} грн'
