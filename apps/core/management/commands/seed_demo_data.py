"""
команда для генерації реалістичних демо-даних:
водії, автобуси, маршрути зі зупинками, рейси, промокоди.

запуск:
    python manage.py seed_demo_data

опції:
    --reset  Видалити існуючі демо-дані перед створенням нових.
"""

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.customers.models import Customer
from apps.fleet.models import Driver, Vehicle
from apps.orders.models import Order, PromoCode, Ticket
from apps.routes.models import Route, Stop, Trip


User = get_user_model()



# дані: водії


DRIVERS = [
    {
        'first_name': 'Іван', 'last_name': 'Петренко', 'patronymic': 'Васильович',
        'phone': '+380 67 123 45 67', 'license_number': 'AAB 123456',
        'categories': 'B, C, D, D1', 'license_year': 2032, 'birth_year': 1978,
        'hire_year': 2018, 'passport_year': 2031,
    },
    {
        'first_name': 'Олександр', 'last_name': 'Коваленко', 'patronymic': 'Михайлович',
        'phone': '+380 50 234 56 78', 'license_number': 'AAC 234567',
        'categories': 'B, D, D1', 'license_year': 2030, 'birth_year': 1985,
        'hire_year': 2020, 'passport_year': 2029,
    },
    {
        'first_name': 'Володимир', 'last_name': 'Шевченко', 'patronymic': 'Петрович',
        'phone': '+380 95 345 67 89', 'license_number': 'AAD 345678',
        'categories': 'B, C, CE, D, D1', 'license_year': 2033, 'birth_year': 1972,
        'hire_year': 2015, 'passport_year': 2032,
    },
    {
        'first_name': 'Андрій', 'last_name': 'Мельник', 'patronymic': 'Юрійович',
        'phone': '+380 63 456 78 90', 'license_number': 'AAE 456789',
        'categories': 'B, D', 'license_year': 2031, 'birth_year': 1988,
        'hire_year': 2021, 'passport_year': 2030,
    },
    {
        'first_name': 'Сергій', 'last_name': 'Бойко', 'patronymic': 'Олегович',
        'phone': '+380 67 567 89 01', 'license_number': 'AAF 567890',
        'categories': 'B, D, D1', 'license_year': 2029, 'birth_year': 1980,
        'hire_year': 2017, 'passport_year': 2028,
    },
    {
        'first_name': 'Михайло', 'last_name': 'Ткаченко', 'patronymic': 'Степанович',
        'phone': '+380 73 678 90 12', 'license_number': 'AAG 678901',
        'categories': 'B, C, D', 'license_year': 2034, 'birth_year': 1975,
        'hire_year': 2014, 'passport_year': 2033,
    },
    {
        'first_name': 'Дмитро', 'last_name': 'Кравченко', 'patronymic': 'Анатолійович',
        'phone': '+380 99 789 01 23', 'license_number': 'AAH 789012',
        'categories': 'B, D, D1', 'license_year': 2032, 'birth_year': 1983,
        'hire_year': 2019, 'passport_year': 2031,
    },
    {
        'first_name': 'Юрій', 'last_name': 'Гриценко', 'patronymic': 'Олексійович',
        'phone': '+380 67 890 12 34', 'license_number': 'AAJ 890123',
        'categories': 'B, D', 'license_year': 2030, 'birth_year': 1990,
        'hire_year': 2022, 'passport_year': 2029,
    },
    {
        'first_name': 'Роман', 'last_name': 'Поліщук', 'patronymic': 'Васильович',
        'phone': '+380 50 901 23 45', 'license_number': 'AAK 901234',
        'categories': 'B, C, D, D1', 'license_year': 2033, 'birth_year': 1981,
        'hire_year': 2016, 'passport_year': 2032,
    },
    {
        'first_name': 'Тарас', 'last_name': 'Лисенко', 'patronymic': 'Іванович',
        'phone': '+380 95 012 34 56', 'license_number': 'AAL 012345',
        'categories': 'B, D, D1', 'license_year': 2031, 'birth_year': 1986,
        'hire_year': 2018, 'passport_year': 2030,
    },
]



# дані: автобуси та мікроавтобуси


VEHICLES = [
    {
        'reg': 'AO 5665 AO', 'brand': 'Mercedes', 'model': 'Tourismo', 'year': 2020,
        'type': 'bus', 'seats': 49, 'class': 'business', 'mileage': 320000,
        'wifi': True, 'wc': True, 'climate': True, 'tv': True, 'usb': True,
        'luggage': Decimal('11.5'), 'fuel': 'diesel',
    },
    {
        'reg': 'AO 7811 BC', 'brand': 'Setra', 'model': 'S 415 HD', 'year': 2019,
        'type': 'bus', 'seats': 53, 'class': 'tourist', 'mileage': 415000,
        'wifi': True, 'wc': True, 'climate': True, 'tv': True, 'usb': True,
        'luggage': Decimal('12.0'), 'fuel': 'diesel',
    },
    {
        'reg': 'AA 4523 IM', 'brand': 'Neoplan', 'model': 'Cityliner', 'year': 2021,
        'type': 'bus', 'seats': 51, 'class': 'luxury', 'mileage': 180000,
        'wifi': True, 'wc': True, 'climate': True, 'tv': True, 'usb': True,
        'luggage': Decimal('13.0'), 'fuel': 'diesel',
    },
    {
        'reg': 'BC 9087 KL', 'brand': 'Van Hool', 'model': 'Astron', 'year': 2018,
        'type': 'bus', 'seats': 49, 'class': 'business', 'mileage': 510000,
        'wifi': True, 'wc': True, 'climate': True, 'tv': False, 'usb': True,
        'luggage': Decimal('11.0'), 'fuel': 'diesel',
    },
    {
        'reg': 'KA 1234 EH', 'brand': 'MAN', 'model': "Lion's Coach", 'year': 2019,
        'type': 'bus', 'seats': 53, 'class': 'tourist', 'mileage': 380000,
        'wifi': True, 'wc': True, 'climate': True, 'tv': True, 'usb': True,
        'luggage': Decimal('12.5'), 'fuel': 'diesel',
    },
    {
        'reg': 'AX 5678 CH', 'brand': 'Volvo', 'model': '9700', 'year': 2020,
        'type': 'bus', 'seats': 51, 'class': 'tourist', 'mileage': 250000,
        'wifi': True, 'wc': True, 'climate': True, 'tv': True, 'usb': True,
        'luggage': Decimal('12.0'), 'fuel': 'diesel',
    },
    {
        'reg': 'BH 3344 MK', 'brand': 'Setra', 'model': 'ComfortClass S 416', 'year': 2017,
        'type': 'bus', 'seats': 49, 'class': 'business', 'mileage': 620000,
        'wifi': True, 'wc': True, 'climate': True, 'tv': False, 'usb': False,
        'luggage': Decimal('11.0'), 'fuel': 'diesel',
    },
    {
        'reg': 'AA 7890 OP', 'brand': 'Mercedes', 'model': 'Travego', 'year': 2022,
        'type': 'bus', 'seats': 50, 'class': 'luxury', 'mileage': 95000,
        'wifi': True, 'wc': True, 'climate': True, 'tv': True, 'usb': True,
        'luggage': Decimal('13.5'), 'fuel': 'diesel',
    },
    {
        'reg': 'AT 2233 LV', 'brand': 'Mercedes', 'model': 'Sprinter 519', 'year': 2021,
        'type': 'minibus', 'seats': 19, 'class': 'tourist', 'mileage': 165000,
        'wifi': True, 'wc': False, 'climate': True, 'tv': False, 'usb': True,
        'luggage': Decimal('4.0'), 'fuel': 'diesel',
    },
    {
        'reg': 'BO 5566 OD', 'brand': 'Iveco', 'model': 'Daily 70C18', 'year': 2020,
        'type': 'minibus', 'seats': 16, 'class': 'economy', 'mileage': 215000,
        'wifi': False, 'wc': False, 'climate': True, 'tv': False, 'usb': True,
        'luggage': Decimal('3.5'), 'fuel': 'diesel',
    },
]



# дані: маршрути та зупинки
# координати реальних автостанцій / центрів міст (lat, lng).


CITIES = {
    'Київ':            ('UA', 50.4501, 30.5234, 'Автостанція "Південна"'),
    'Львів':           ('UA', 49.8397, 24.0297, 'Головний автовокзал'),
    'Ужгород':         ('UA', 48.6233, 22.2950, 'Автостанція "АС-1"'),
    'Чернівці':        ('UA', 48.2922, 25.9358, 'Центральний автовокзал'),
    'Одеса':           ('UA', 46.4825, 30.7233, 'Автостанція "Привоз"'),
    'Харків':          ('UA', 49.9935, 36.2304, 'Автостанція №1'),
    'Житомир':         ('UA', 50.2547, 28.6587, 'Центральна автостанція'),
    'Рівне':           ('UA', 50.6199, 26.2516, 'Автостанція'),
    'Чоп':             ('UA', 48.4337, 22.2024, 'Залізнична станція'),
    'Дніпро':          ('UA', 48.4647, 35.0462, 'Автовокзал "Центральний"'),
    'Запоріжжя':       ('UA', 47.8388, 35.1396, 'Автостанція №1'),
    'Тернопіль':       ('UA', 49.5535, 25.5947, 'Автовокзал'),
    'Івано-Франківськ': ('UA', 48.9226, 24.7111, 'Автостанція №1'),
    'Хмельницький':    ('UA', 49.4229, 26.9871, 'Автовокзал'),
    'Перемишль':  ('PL', 49.7838, 22.7677, 'Dworzec autobusowy'),
    'Краків':     ('PL', 50.0647, 19.9450, 'MDA Kraków'),
    'Тарнів':     ('PL', 50.0121, 20.9858, 'Dworzec PKS'),
    'Варшава':    ('PL', 52.2297, 21.0122, 'Dworzec Zachodni'),
    'Вроцлав':    ('PL', 51.1079, 17.0385, 'Dworzec autobusowy'),
    'Брно':       ('CZ', 49.1951, 16.6068, 'ÚAN Zvonařka'),
    'Прага':      ('CZ', 50.0755, 14.4378, 'ÚAN Florenc'),
    'Кошице':     ('SK', 48.7164, 21.2611, 'Hlavná autobusová stanica'),
    'Жиліна':     ('SK', 49.2237, 18.7397, 'AS Žilina'),
    'Тренчин':    ('SK', 48.8945, 18.0444, 'AS Trenčín'),
    'Братислава': ('SK', 48.1486, 17.1077, 'AS Mlynské nivy'),
    'Захонь':     ('HU', 48.4060, 22.1881, 'Záhony Vasútállomás'),
    'Дебрецен':   ('HU', 47.5316, 21.6273, 'Debrecen autóbusz-állomás'),
    'Будапешт':   ('HU', 47.4979, 19.0402, 'Népliget autóbusz-pályaudvar'),
    'Відень':     ('AT', 48.2082, 16.3738, 'Wien Hauptbahnhof'),
    'Сучава':     ('RO', 47.6544, 26.2575, 'Autogară Suceava'),
    'Брашов':     ('RO', 45.6580, 25.6012, 'Autogară Bartolomeu'),
    'Бухарест':   ('RO', 44.4268, 26.1025, 'Autogara Militari'),
    'Кишинів':    ('MD', 47.0105, 28.8638, 'Gara de Sud'),
    'Дрезден':    ('DE', 51.0504, 13.7373, 'ZOB Dresden'),
    'Берлін':     ('DE', 52.5200, 13.4050, 'ZOB Berlin'),
    'Нюрнберг':   ('DE', 49.4521, 11.0767, 'Nürnberg ZOB'),
    'Мюнхен':     ('DE', 48.1351, 11.5820, 'München ZOB'),
}


def stop_data(city, order, arrival_offset, departure_offset, can_board=True, can_alight=True):
    code, lat, lng, station = CITIES[city]
    return {
        'order': order, 'country': code, 'city': city, 'station': station,
        'lat': lat, 'lng': lng, 'arrival': arrival_offset, 'departure': departure_offset,
        'board': can_board, 'alight': can_alight,
    }


# кожен маршрут: (код, назва, відстань, тривалість_хв, базова_ціна_EUR, [зупинки...])
ROUTES = [
    # існуючий буде оновлений
    ('UA-CZ-001', 'Ужгород - Прага', 1080, 1080, 80, [
        stop_data('Ужгород', 1, 0, 10),
        stop_data('Кошице', 2, 90, 105),
        stop_data('Брно', 3, 850, 870),
        stop_data('Прага', 4, 1080, 1080),
    ]),
    ('UA-PL-001', 'Київ - Варшава', 880, 900, 50, [
        stop_data('Київ', 1, 0, 10),
        stop_data('Житомир', 2, 90, 105),
        stop_data('Рівне', 3, 220, 235),
        stop_data('Львів', 4, 380, 410),
        stop_data('Перемишль', 5, 530, 560),
        stop_data('Краків', 6, 680, 700),
        stop_data('Варшава', 7, 900, 900),
    ]),
    ('UA-PL-002', 'Львів - Краків', 320, 360, 35, [
        stop_data('Львів', 1, 0, 10),
        stop_data('Перемишль', 2, 130, 160),
        stop_data('Тарнів', 3, 270, 285),
        stop_data('Краків', 4, 360, 360),
    ]),
    ('UA-CZ-002', 'Київ - Прага', 1450, 1620, 95, [
        stop_data('Київ', 1, 0, 10),
        stop_data('Львів', 2, 380, 410),
        stop_data('Краків', 3, 700, 720),
        stop_data('Брно', 4, 1380, 1400),
        stop_data('Прага', 5, 1620, 1620),
    ]),
    ('UA-DE-001', 'Київ - Берлін', 1750, 1860, 110, [
        stop_data('Київ', 1, 0, 10),
        stop_data('Львів', 2, 380, 410),
        stop_data('Краків', 3, 700, 720),
        stop_data('Вроцлав', 4, 970, 990),
        stop_data('Дрезден', 5, 1450, 1470),
        stop_data('Берлін', 6, 1860, 1860),
    ]),
    ('UA-AT-001', 'Львів - Відень', 970, 1080, 75, [
        stop_data('Львів', 1, 0, 10),
        stop_data('Будапешт', 2, 690, 720),
        stop_data('Відень', 3, 1080, 1080),
    ]),
    ('UA-RO-001', 'Чернівці - Бухарест', 580, 720, 55, [
        stop_data('Чернівці', 1, 0, 10),
        stop_data('Сучава', 2, 100, 115),
        stop_data('Брашов', 3, 470, 490),
        stop_data('Бухарест', 4, 720, 720),
    ]),
    ('UA-MD-001', 'Одеса - Кишинів', 200, 240, 20, [
        stop_data('Одеса', 1, 0, 10),
        stop_data('Кишинів', 2, 240, 240),
    ]),
    ('UA-HU-001', 'Ужгород - Будапешт', 480, 540, 40, [
        stop_data('Ужгород', 1, 0, 10),
        stop_data('Чоп', 2, 30, 45),
        stop_data('Захонь', 3, 60, 90),
        stop_data('Дебрецен', 4, 240, 260),
        stop_data('Будапешт', 5, 540, 540),
    ]),
    ('UA-SK-001', 'Львів - Братислава', 760, 870, 65, [
        stop_data('Львів', 1, 0, 10),
        stop_data('Кошице', 2, 320, 345),
        stop_data('Жиліна', 3, 540, 555),
        stop_data('Тренчин', 4, 660, 675),
        stop_data('Братислава', 5, 870, 870),
    ]),
    ('UA-DE-002', 'Львів - Мюнхен', 1500, 1680, 105, [
        stop_data('Львів', 1, 0, 10),
        stop_data('Краків', 2, 320, 345),
        stop_data('Прага', 3, 920, 950),
        stop_data('Нюрнберг', 4, 1320, 1340),
        stop_data('Мюнхен', 5, 1680, 1680),
    ]),
    ('UA-CZ-003', 'Харків - Прага', 1900, 2160, 115, [
        stop_data('Харків', 1, 0, 10),
        stop_data('Київ', 2, 380, 410),
        stop_data('Львів', 3, 800, 830),
        stop_data('Краків', 4, 1140, 1160),
        stop_data('Прага', 5, 2160, 2160),
    ]),
    ('UA-PL-003', 'Дніпро - Варшава', 1300, 1500, 75, [
        stop_data('Дніпро', 1, 0, 10),
        stop_data('Київ', 2, 380, 410),
        stop_data('Житомир', 3, 480, 495),
        stop_data('Львів', 4, 760, 790),
        stop_data('Краків', 5, 1080, 1100),
        stop_data('Варшава', 6, 1500, 1500),
    ]),
    ('UA-PL-004', 'Тернопіль - Вроцлав', 720, 840, 55, [
        stop_data('Тернопіль', 1, 0, 10),
        stop_data('Львів', 2, 130, 150),
        stop_data('Краків', 3, 480, 500),
        stop_data('Вроцлав', 4, 840, 840),
    ]),
    ('UA-PL-005', 'Івано-Франківськ - Краків', 410, 480, 40, [
        stop_data('Івано-Франківськ', 1, 0, 10),
        stop_data('Львів', 2, 130, 150),
        stop_data('Перемишль', 3, 250, 270),
        stop_data('Краків', 4, 480, 480),
    ]),
    ('UA-DE-003', 'Запоріжжя - Берлін', 2200, 2520, 130, [
        stop_data('Запоріжжя', 1, 0, 10),
        stop_data('Дніпро', 2, 90, 105),
        stop_data('Київ', 3, 470, 500),
        stop_data('Львів', 4, 850, 880),
        stop_data('Краків', 5, 1170, 1190),
        stop_data('Вроцлав', 6, 1450, 1470),
        stop_data('Дрезден', 7, 1950, 1970),
        stop_data('Берлін', 8, 2520, 2520),
    ]),
    ('UA-HU-002', 'Чернівці - Будапешт', 740, 870, 60, [
        stop_data('Чернівці', 1, 0, 10),
        stop_data('Івано-Франківськ', 2, 150, 170),
        stop_data('Ужгород', 3, 470, 500),
        stop_data('Дебрецен', 4, 690, 710),
        stop_data('Будапешт', 5, 870, 870),
    ]),
]


PROMOS = [
    {'code': 'SUMMER15', 'desc': 'Літня знижка 15%', 'percent': 15, 'days': 90},
    {'code': 'STUDENT10', 'desc': 'Студентська знижка', 'percent': 10, 'days': 365},
    {'code': 'EARLYBIRD', 'desc': 'Раннє бронювання', 'percent': 12, 'days': 60},
    {'code': 'WELCOME5', 'desc': 'Бонус новачкам', 'percent': 5, 'days': 365},
]


class Command(BaseCommand):
    help = 'Створює реалістичні демо-дані для платформи'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Видалити існуючі демо-дані')
        parser.add_argument('--yes-i-am-sure', action='store_true',
                            help='Дозволити --reset у production (DEBUG=False). '
                                 'Без цього прапорця у production команда відмовиться '
                                 'видаляти дані.')

    def handle(self, *args, **options):
        from django.conf import settings

        if options['reset']:
            # захист від випадкового запуску у production: --reset знесе усі дані.
            if not settings.DEBUG and not options['yes_i_am_sure']:
                self.stdout.write(self.style.ERROR(
                    'ВІДМОВА: --reset у production-режимі (DEBUG=False) видалить '
                    'усі рейси, замовлення, водіїв, авто і маршрути. Якщо ви точно '
                    'розумієте що робите - додайте --yes-i-am-sure.'
                ))
                return

            self.stdout.write('Видалення існуючих демо-даних...')
            Ticket.objects.all().delete()
            Order.objects.all().delete()
            Trip.objects.all().delete()
            Stop.objects.all().delete()
            Driver.objects.all().delete()
            Vehicle.objects.all().delete()
            Route.objects.all().delete()
            User.objects.filter(role=User.Role.DRIVER).delete()
            PromoCode.objects.all().delete()

        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stdout.write(self.style.ERROR('Спершу створи суперюзера: python manage.py createsuperuser'))
            return

        # водії
        drivers = self._create_drivers()
        self.stdout.write(self.style.SUCCESS(f'Водіїв створено: {len(drivers)}'))

        # автобуси
        vehicles = self._create_vehicles()
        self.stdout.write(self.style.SUCCESS(f'Транспортних засобів створено: {len(vehicles)}'))

        # маршрути
        routes = self._create_routes()
        self.stdout.write(self.style.SUCCESS(f'Маршрутів створено: {len(routes)}'))

        #промокоди
        self._create_promos()
        self.stdout.write(self.style.SUCCESS(f'Промокодів створено: {len(PROMOS)}'))

        # рейси
        buses = [v for v in vehicles if v.is_passenger]
        trips_count = self._create_trips(routes, buses, drivers)
        self.stdout.write(self.style.SUCCESS(f'Рейсів створено: {trips_count}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Демо-дані успішно створено.'))



    def _create_drivers(self):
        drivers = []
        for d in DRIVERS:
            username = f"{d['last_name'].lower()}.{d['first_name'][:3].lower()}"
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    'first_name': d['first_name'],
                    'last_name': d['last_name'],
                    'patronymic': d['patronymic'],
                    'email': f"{username}@transauto.travel",
                    'phone': d['phone'],
                    'role': User.Role.DRIVER,
                    'is_staff': False,
                    'is_active': True,
                },
            )
            user.set_password('demo12345')
            user.save()

            driver, _ = Driver.objects.update_or_create(
                user=user,
                defaults={
                    'license_number': d['license_number'],
                    'license_categories': d['categories'],
                    'license_expiry': date(d['license_year'], 12, 1),
                    'date_of_birth': date(d['birth_year'], random.randint(1, 12), random.randint(1, 28)),
                    'date_of_hire': date(d['hire_year'], random.randint(1, 12), random.randint(1, 28)),
                    'nationality': 'Україна',
                    'passport_number': f"FA{random.randint(100000, 999999)}",
                    'passport_expiry': date(d['passport_year'], 12, 1),
                    'medical_check_expiry': date(2027, random.randint(1, 12), random.randint(1, 28)),
                    'is_available': True,
                },
            )
            drivers.append(driver)
        return drivers

    def _create_vehicles(self):
        vehicles = []
        for v in VEHICLES:
            obj, _ = Vehicle.objects.update_or_create(
                registration_number=v['reg'],
                defaults={
                    'vehicle_type': v['type'],
                    'brand': v['brand'],
                    'model': v['model'],
                    'year': v['year'],
                    'color': random.choice(['Білий', 'Сірий металік', 'Темно-синій', 'Чорний']),
                    'fuel_type': v['fuel'],
                    'mileage_km': v['mileage'],
                    'date_acquired': date(v['year'], random.randint(1, 12), random.randint(1, 28)),
                    'insurance_expiry': date(2027, 6, 1),
                    'last_inspection_date': date(2026, random.randint(1, 4), random.randint(1, 28)),
                    'next_inspection_date': date(2027, random.randint(1, 4), random.randint(1, 28)),
                    'seats_total': v['seats'],
                    'comfort_class': v['class'],
                    'has_wifi': v['wifi'],
                    'has_wc': v['wc'],
                    'has_climate': v['climate'],
                    'has_tv': v['tv'],
                    'has_usb': v['usb'],
                    'luggage_volume_m3': v['luggage'],
                    'is_active': True,
                },
            )
            vehicles.append(obj)
        return vehicles

    def _create_routes(self):
        routes = []
        for code, name, distance, duration, price, stops in ROUTES:
            origin_country = stops[0]['country']
            origin_city = stops[0]['city']
            dest_country = stops[-1]['country']
            dest_city = stops[-1]['city']

            route, _ = Route.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'origin_country': origin_country,
                    'origin_city': origin_city,
                    'destination_country': dest_country,
                    'destination_city': dest_city,
                    'distance_km': distance,
                    'duration_minutes': duration,
                    'description': f'Регулярний маршрут {name}. Зупинки в основних містах. Базова ціна {price} EUR.',
                    'is_active': True,
                },
            )
            # перестворюю зупинки
            route.stops.all().delete()
            for s in stops:
                Stop.objects.create(
                    route=route,
                    order=s['order'],
                    country=s['country'],
                    city=s['city'],
                    station_name=s['station'],
                    address='',
                    latitude=Decimal(str(s['lat'])),
                    longitude=Decimal(str(s['lng'])),
                    arrival_offset_minutes=s['arrival'],
                    departure_offset_minutes=s['departure'],
                    can_board=s['board'],
                    can_alight=s['alight'],
                )
            routes.append((route, price))
        return routes

    def _create_promos(self):
        today = timezone.now().date()
        for p in PROMOS:
            PromoCode.objects.update_or_create(
                code=p['code'],
                defaults={
                    'description': p['desc'],
                    'discount_percent': p['percent'],
                    'valid_from': today,
                    'valid_until': today + timedelta(days=p['days']),
                    'usage_limit': 0,
                    'is_active': True,
                },
            )

    def _create_trips(self, routes, buses, drivers):
        """
        Рейси з січня по серпень 2026.
        Популярні маршрути отримують більше рейсів (по 2 на тиждень),
        менш популярні — кілька на місяць.
        """
        Trip.objects.all().delete()

        now = timezone.now()
        created = 0

        bus_drivers = [d for d in drivers if d.can_drive_bus]

        # період: 01.01.2026 — 31.08.2026
        start = datetime(2026, 1, 1, tzinfo=timezone.get_current_timezone())
        end = datetime(2026, 8, 31, tzinfo=timezone.get_current_timezone())

        # частота рейсів на тиждень для кожного маршруту (за порядком у ROUTES)
        weekly_frequency = {
            'UA-CZ-001': 3,   # Ужгород-Прага: 3 на тиждень
            'UA-PL-001': 4,   # Київ-Варшава: 4 на тиждень
            'UA-PL-002': 5,   # Львів-Краків: 5 на тиждень
            'UA-CZ-002': 3,   # Київ-Прага: 3 на тиждень
            'UA-DE-001': 2,   # Київ-Берлін: 2 на тиждень
            'UA-AT-001': 2,   # Львів-Відень: 2 на тиждень
            'UA-RO-001': 2,   # Чернівці-Бухарест: 2 на тиждень
            'UA-MD-001': 4,   # Одеса-Кишинів: 4 на тиждень
            'UA-HU-001': 3,   # Ужгород-Будапешт: 3 на тиждень
            'UA-SK-001': 2,   # Львів-Братислава: 2 на тиждень
            'UA-DE-002': 2,   # Львів-Мюнхен: 2 на тиждень
            'UA-CZ-003': 1,   # Харків-Прага: 1 на тиждень
            'UA-PL-003': 2,   # Дніпро-Варшава: 2 на тиждень
            'UA-PL-004': 2,   # Тернопіль-Вроцлав: 2 на тиждень
            'UA-PL-005': 3,   # Івано-Франківськ-Краків: 3 на тиждень
            'UA-DE-003': 1,   # Запоріжжя-Берлін: 1 на тиждень
            'UA-HU-002': 2,   # Чернівці-Будапешт: 2 на тиждень
        }

        # дні тижня для кожної частоти (0=пн, 6=нд)
        weekday_schedule = {
            1: [4],
            2: [1, 4],
            3: [1, 3, 5],
            4: [1, 3, 5, 6],
            5: [0, 2, 4, 5, 6],
        }

        # можливі години відправлення
        morning_hours = [6, 7, 8, 9]
        evening_hours = [18, 19, 20, 21, 22]

        for route, base_price in routes:
            freq = weekly_frequency.get(route.code, 2)
            schedule_days = weekday_schedule.get(freq, [1, 4])

            current = start
            while current <= end:
                if current.weekday() in schedule_days:
                    # більшість рейсів вранці, частина ввечері
                    hour = random.choice(
                        morning_hours if random.random() < 0.6 else evening_hours
                    )
                    departure = current.replace(
                        hour=hour, minute=random.choice([0, 15, 30]),
                        second=0, microsecond=0,
                    )

                    bus = random.choice(buses)
                    main_driver = random.choice(bus_drivers)
                    co_driver = None
                    if route.distance_km > 700:
                        pool = [d for d in bus_drivers if d.id != main_driver.id]
                        if pool:
                            co_driver = random.choice(pool)

                    # статус залежить від часу
                    if departure < now - timedelta(days=2):
                        status = random.choices(
                            ['completed', 'cancelled'],
                            weights=[92, 8],
                        )[0]
                    elif departure < now + timedelta(days=2):
                        status = random.choices(
                            ['in_progress', 'on_sale', 'completed'],
                            weights=[15, 60, 25],
                        )[0]
                    else:
                        status = random.choices(
                            ['on_sale', 'planned'],
                            weights=[80, 20],
                        )[0]

                    # сезонність: літо дорожче, січень-лютий дешевше
                    season_mod = {
                        1: -8, 2: -8, 3: -3, 4: 0, 5: 5,
                        6: 10, 7: 12, 8: 12,
                    }.get(departure.month, 0)
                    price_var = random.choice([-3, 0, 0, 0, 3])
                    price = max(15, base_price + season_mod + price_var)

                    Trip.objects.create(
                        route=route,
                        departure_at=departure,
                        vehicle=bus,
                        main_driver=main_driver,
                        co_driver=co_driver,
                        status=status,
                        base_price=Decimal(str(price)),
                        currency='EUR',
                        notes='',
                    )
                    created += 1

                current += timedelta(days=1)

        return created
