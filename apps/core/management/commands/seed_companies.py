"""
створює корпоративних клієнтів-юридичних осіб і прив'язує до них
частину існуючих замовлень для гарної демонстрації.

запуск:
    python manage.py seed_companies
"""

import random

from django.core.management.base import BaseCommand

from apps.customers.models import Customer
from apps.orders.models import Order


COMPANIES = [
    {
        'name': 'Турагенція "Карпати-Тур"', 'legal_name': 'ТОВ "Карпати-Тур"',
        'tax_number': '38291746', 'country': 'UA', 'city': 'Ужгород',
        'address': 'вул. Корзо, 7, оф. 12',
        'contact_person': 'Іванов Ігор Степанович',
        'contact_phone': '+380 312 442 156', 'contact_email': 'office@karpaty-tour.ua',
        'website': 'https://karpaty-tour.ua', 'payment_terms_days': 14,
    },
    {
        'name': 'Студентські поїздки', 'legal_name': 'ГО "Студентські поїздки"',
        'tax_number': '41526378', 'country': 'UA', 'city': 'Львів',
        'address': 'просп. Свободи, 22',
        'contact_person': 'Гончар Олена Михайлівна',
        'contact_phone': '+380 322 297 488', 'contact_email': 'travel@stud.org.ua',
        'website': '', 'payment_terms_days': 30,
    },
    {
        'name': 'EuroTrip Sp. z o.o.', 'legal_name': 'EuroTrip Sp. z o.o.',
        'tax_number': '', 'vat_number': 'PL5260123456',
        'country': 'PL', 'city': 'Варшава',
        'address': 'ul. Marszałkowska 100',
        'contact_person': 'Kowalski Marek',
        'contact_phone': '+48 22 555 12 34', 'contact_email': 'orders@eurotrip.pl',
        'website': 'https://eurotrip.pl', 'payment_terms_days': 21,
    },
    {
        'name': 'Готель "Едельвейс"', 'legal_name': 'ТОВ "Готель Едельвейс"',
        'tax_number': '32987561', 'country': 'UA', 'city': 'Чернівці',
        'address': 'вул. Головна, 145',
        'contact_person': 'Левченко Тетяна',
        'contact_phone': '+380 372 514 770', 'contact_email': 'reception@edelweiss.ua',
        'website': 'https://edelweiss.ua', 'payment_terms_days': 14,
    },
    {
        'name': 'BohemiaBus s.r.o.', 'legal_name': 'BohemiaBus s.r.o.',
        'tax_number': '', 'vat_number': 'CZ27894561',
        'country': 'CZ', 'city': 'Прага',
        'address': 'Václavské náměstí 1',
        'contact_person': 'Novák Jan',
        'contact_phone': '+420 224 156 789', 'contact_email': 'partner@bohemiabus.cz',
        'website': 'https://bohemiabus.cz', 'payment_terms_days': 30,
    },
    {
        'name': 'Корпорація "Західбуд"', 'legal_name': 'ПАТ "Західбуд"',
        'tax_number': '14782536', 'country': 'UA', 'city': 'Львів',
        'address': 'вул. Городоцька, 174',
        'contact_person': 'Стельмах Юрій Петрович',
        'contact_phone': '+380 322 998 156', 'contact_email': 'travel@zahidbud.com.ua',
        'website': 'https://zahidbud.com.ua', 'payment_terms_days': 45,
    },
    {
        'name': 'Спортклуб "Динамо-Закарпаття"', 'legal_name': 'ГО "СК Динамо-Закарпаття"',
        'tax_number': '38456712', 'country': 'UA', 'city': 'Ужгород',
        'address': 'вул. Спортивна, 4',
        'contact_person': 'Бойко Сергій Олегович',
        'contact_phone': '+380 312 651 449', 'contact_email': 'team@dynamo-zk.ua',
        'website': '', 'payment_terms_days': 14,
    },
    {
        'name': 'BudapestBound Kft.', 'legal_name': 'BudapestBound Kft.',
        'tax_number': '', 'vat_number': 'HU12345678',
        'country': 'HU', 'city': 'Будапешт',
        'address': 'Andrássy út 50',
        'contact_person': 'Nagy Péter',
        'contact_phone': '+36 1 555 7890', 'contact_email': 'office@budapestbound.hu',
        'website': 'https://budapestbound.hu', 'payment_terms_days': 30,
    },
]


class Command(BaseCommand):
    help = 'Створює корпоративних клієнтів і прив\'язує до них частину замовлень'

    def handle(self, *args, **options):
        created = 0
        customers = []
        for c in COMPANIES:
            obj, was_created = Customer.objects.update_or_create(
                name=c['name'],
                defaults={k: v for k, v in c.items() if k != 'name'},
            )
            customers.append(obj)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Компаній додано/оновлено: {len(customers)} (нових {created})'))

        # прив'язую випадкові 600 замовлень до компаній
        unassigned = Order.objects.filter(customer__isnull=True).order_by('?')[:600]
        unassigned_ids = list(unassigned.values_list('id', flat=True))
        linked = 0
        for oid in unassigned_ids:
            company = random.choice(customers)
            Order.objects.filter(pk=oid).update(customer=company)
            linked += 1

        self.stdout.write(self.style.SUCCESS(
            f'Прив\'язано {linked} замовлень до корпоративних клієнтів.'
        ))
