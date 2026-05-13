# TransAuto Travel

Веб-застосунок для підтримки діяльності міжнародної транспортної компанії, що спеціалізується на пасажирських автобусних перевезеннях між Україною та країнами ЄС. Дипломна робота, спеціальність 122 «Комп'ютерні науки», ДВНЗ «Ужгородський національний університет».

## Можливості

**Клієнтський портал** (`/`):
- пошук рейсів за містами і датою з підказками-альтернативами;
- покрокове бронювання з вибором місця у схемі автобуса;
- особистий кабінет з історією поїздок, бонусною програмою, відгуками;
- псевдо-онлайн-оплата картою (демо-шлюз);
- стеження за рейсом у реальному часі (GPS-симуляція з прив'язкою до OSRM-маршруту);
- двомовність UA/EN.

**Диспетчерська панель** (`/manage/`):
- дашборд з графіками (Chart.js): виручка факт + прогноз, рейси за статусом, топ-маршрути;
- календар рейсів через FullCalendar;
- CRUD клієнтів, автопарку, водіїв, маршрутів;
- журнал аудиту (хто, коли, що змінив);
- експорт замовлень і рейсів у Excel;
- темна тема.

**Документи**:
- PDF квитка з QR-кодом;
- PDF посадкового листа.

**Автоматика**:
- middleware раз на 5 хв оновлює статуси рейсів (planned -> in_progress -> completed);
- сигнали нараховують бали лояльності і відправляють листи-підтвердження;
- transaction.atomic + select_for_update захищає від race conditions при бронюванні останнього місця.

## Стек технологій

| Компонент | Версія |
| --- | --- |
| Python | 3.12+ |
| Django | 6.0 |
| PostgreSQL | 18 |
| Bootstrap | 5.3.3 |
| Chart.js | 4.4.1 |
| Leaflet + OSRM | 1.9.4 |
| FullCalendar | 6.1.11 |
| ReportLab + qrcode | для PDF |
| openpyxl | для Excel |

## Як запустити локально

### Передумови

- Python 3.12+
- PostgreSQL 18+ запущена локально
- Створена БД `transport_db` з користувачем `postgres`

### Кроки

```bash
# 1. Клонування і віртуальне оточення
cd transport_app
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# 2. Залежності
pip install -r requirements.txt

# 3. Конфігурація
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/Mac
# Відкрийте .env і заповніть SECRET_KEY, DATABASE_PASSWORD

# 4. Згенеруйте SECRET_KEY (вставте у .env):
python -c "import secrets; print(secrets.token_urlsafe(50))"

# 5. Міграції
python manage.py migrate

# 6. Адмін-користувач
python manage.py createsuperuser

# 7. Демо-дані (~1500 рейсів, 23k замовлень, 37k квитків)
python manage.py seed_demo_data
python manage.py seed_bookings
python manage.py seed_reviews

# 8. Запуск
python manage.py runserver
```

Доступні URL після запуску:
- `http://127.0.0.1:8000/` - клієнтський сайт
- `http://127.0.0.1:8000/manage/` - диспетчер (логін як superuser)
- `http://127.0.0.1:8000/admin/` - Django admin

### Якщо PowerShell не приймає кирилицю

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python manage.py runserver
```

## Структура проекту

```
transport_app/
  config/                 # settings.py, urls.py
  apps/
    accounts/             # User з ролями + бонусні бали
    customers/            # Корпоративні клієнти
    fleet/                # Vehicle + Driver
    routes/               # Route, Stop, Trip
    orders/               # Order, Ticket, PromoCode + signals
    reviews/              # Review про рейс
    documents/            # PDF (services.py)
    core/                 # Диспетчерська панель /manage/ + middleware
    portal/               # Публічний сайт + booking_service.py + gps_simulator.py
  templates/              # Загальні шаблони
  static/                 # CSS, JS, картинки
  manage.py
  requirements.txt
  .env.example
```

## Корисні management-команди

```bash
# Скинути і заповнити демо-дані заново
python manage.py seed_demo_data --reset
python manage.py seed_bookings --reset

# Заповнити "пробіли" у графіку виручки за останні 14 днів
python manage.py fill_recent_bookings --days 14 --orders-per-day 60

# Виправити квитки де висадка раніше за посадку
python manage.py fix_ticket_stops

# Розподілити дати замовлень рівномірно (1-90 днів до рейсу)
python manage.py redistribute_order_dates

# Оновити статуси рейсів (зазвичай це робить middleware автоматично)
python manage.py update_trip_statuses
```

## Production-deploy

1. Встановити `DEBUG=False` у `.env`, заповнити `ALLOWED_HOSTS`
2. Згенерувати новий `SECRET_KEY`, не використовувати дефолтний
3. Виконати `python manage.py collectstatic`
4. Запустити через `gunicorn config.wsgi:application` (приклад):
   ```bash
   gunicorn --workers 4 --bind 0.0.0.0:8000 config.wsgi:application
   ```
5. Поставити nginx як reverse-proxy з SSL-сертифікатом (Let's Encrypt)
6. Опційно: підключити Redis для кешу через `CACHE_BACKEND` у `.env`
7. Перевести email на справжній SMTP (через `EMAIL_BACKEND`)
8. Налаштувати cron/systemd-timer на `python manage.py update_trip_statuses` щогодини

## Безпека

- transaction.atomic + select_for_update захищають бронювання від race conditions
- IDOR-перевірки на доступ до чужих замовлень, квитків, PDF
- AUTH_PASSWORD_VALIDATORS обмежують слабкі паролі (мін. 8 символів, не суцільні цифри)
- Захист від open redirect через `url_has_allowed_host_and_scheme`
- У production: SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, HSTS, X_FRAME_OPTIONS=DENY

## Автор

Калабішка Ярослав, 4 курс, спеціальність «Комп'ютерні науки», ДВНЗ УжНУ, 2026.
