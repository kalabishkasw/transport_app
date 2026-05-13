"""
Створює тестові відгуки про завершені рейси.
"""

import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.orders.models import Order
from apps.reviews.models import Review


User = get_user_model()


REVIEWS_POSITIVE = [
    ('Все на найвищому рівні', 'Дуже зручний автобус, водії ввічливі, відправлення вчасно. Рекомендую.'),
    ('Чудова поїздка', 'Чисто, тепло, Wi-Fi працював всю дорогу. Місця м\'які, спинки відкидаються.'),
    ('Все сподобалось', 'Купив квиток онлайн за 5 хвилин. На посадці без черг. Прибули раніше графіка.'),
    ('Без зауважень', 'Гарний сервіс, водії вели обережно, зупинки на каві були приємні. Поїдемо ще.'),
    ('Все організовано', 'Перетин кордону зайняв мінімум часу, водій усе пояснив. Якісний рівень.'),
    ('Сучасний автобус', 'Кондиціонер, USB, туалет — все працює. Завжди буду користуватись.'),
    ('Приємно здивовані', 'Очікували значно гірше за такою ціною, але все на висоті.'),
    ('Швидко та комфортно', 'Прибули за графіком. Багажне відділення велике, туди влізла велика сумка.'),
    ('Найкращий вибір', 'Не перший раз їжджу цим маршрутом. Завжди стабільна якість.'),
    ('Дякую', 'Душевно та з турботою. Водій навіть допоміг із багажем. Молодці!'),
]

REVIEWS_NEUTRAL = [
    ('Загалом непогано', 'Поїздка була нормальною. Невеликі затримки на кордоні, але це не від компанії.'),
    ('Так собі', 'Все виконано. Очікував трохи більше комфорту за таку ціну.'),
    ('Звичайний рейс', 'Нічого не скажеш поганого, але і нічого видатного. Звичайний транспорт.'),
    ('Можна краще', 'Все добре, але кондиціонер дув занадто сильно. Бажано регулювати індивідуально.'),
]

REVIEWS_NEGATIVE = [
    ('Запізнення', 'Виїхали з затримкою 40 хвилин без пояснень. Не вистачило інформування.'),
    ('Незручно', 'Місця близько, ноги затерпли. Для довгих рейсів треба автобуси з більшим простором.'),
]


class Command(BaseCommand):
    help = 'Створює тестові відгуки до завершених замовлень'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=80,
                            help='Скільки відгуків створити (default 80)')
        parser.add_argument('--reset', action='store_true', help='Видалити існуючі відгуки')

    def handle(self, *args, **options):
        if options['reset']:
            Review.objects.all().delete()
            self.stdout.write('Існуючі відгуки видалено.')

        # Беремо клієнтів. Якщо їх мало — створимо кілька
        clients = list(User.objects.filter(role=User.Role.CLIENT))
        if len(clients) < 5:
            clients += self._create_demo_clients()

        completed = list(
            Order.objects
            .filter(status=Order.Status.COMPLETED)
            .select_related('trip')[:1000]
        )
        if not completed:
            self.stdout.write(self.style.WARNING('Немає завершених замовлень.'))
            return

        target = min(options['count'], len(completed))
        sampled = random.sample(completed, target)

        created = 0
        for order in sampled:
            user = random.choice(clients)
            # Унікальність trip+user
            if Review.objects.filter(trip=order.trip, user=user).exists():
                continue
            rating, title, comment = self._random_review()
            Review.objects.create(
                trip=order.trip,
                user=user,
                order=order,
                rating=rating,
                title=title,
                comment=comment,
            )
            created += 1

        # Нараховуємо балів кільком клієнтам, для демо
        for u in clients:
            u.loyalty_points = random.choice([50, 120, 280, 540, 90, 360])
            u.save(update_fields=['loyalty_points'])

        self.stdout.write(self.style.SUCCESS(
            f'Створено {created} відгуків. Нараховано бали {len(clients)} клієнтам.'
        ))

    def _random_review(self):
        # 75% позитивних, 20% нейтральних, 5% негативних
        bucket = random.choices(
            ['positive', 'neutral', 'negative'],
            weights=[75, 20, 5],
        )[0]
        if bucket == 'positive':
            title, comment = random.choice(REVIEWS_POSITIVE)
            rating = random.choices([5, 4], weights=[70, 30])[0]
        elif bucket == 'neutral':
            title, comment = random.choice(REVIEWS_NEUTRAL)
            rating = 3
        else:
            title, comment = random.choice(REVIEWS_NEGATIVE)
            rating = random.choice([1, 2])
        return rating, title, comment

    def _create_demo_clients(self):
        names = [
            ('Олексій', 'Кузьменко'), ('Марія', 'Шевчук'), ('Денис', 'Ромащенко'),
            ('Ангеліна', 'Левченко'), ('Тарас', 'Білий'), ('Юлія', 'Орлик'),
            ('Андрій', 'Стельмах'), ('Олена', 'Карпенко'),
        ]
        created = []
        for first, last in names:
            username = f'{last.lower()}.{first[:3].lower()}@gmail.com'
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    'first_name': first, 'last_name': last,
                    'email': username, 'role': User.Role.CLIENT,
                    'is_active': True,
                },
            )
            user.set_password('demo12345')
            user.save()
            created.append(user)
        return created
