# TransAuto Travel

Веб-застосунок для міжнародної транспортної компанії: пасажирські автобусні рейси з України до країн ЄС. Дипломна робота, спеціальність 122 «Комп'ютерні науки», ДВНЗ «Ужгородський національний університет», 2026.

Онлайн: https://transauto-travel.onrender.com

## Що вміє

Клієнтський сайт `/`:
- пошук рейсів за містами і датою, з підказками альтернатив якщо нічого не знайшлося,
- бронювання з вибором місця, контактів пасажирів, посадки/висадки,
- mock-оплата карткою (анімований платіжний шлюз для демо),
- стеження за рейсом у реальному часі з GPS-симуляцією і snap-to-road через OSRM,
- особистий кабінет: історія поїздок, бонусні бали, відгуки,
- двомовність UA/EN.

Диспетчерська `/manage/`:
- дашборд з графіками виручки (факт + прогноз), розподілом рейсів за статусом, топ-маршрутами,
- календар рейсів (FullCalendar),
- список замовлень з фільтрами і bulk-діями,
- список ТЗ, водіїв, клієнтів, маршрутів,
- журнал аудиту: хто що коли змінив,
- експорт у Excel.

Документи:
- PDF квитка з QR-кодом,
- PDF посадкового листа для водія.

## Стек

| Шар | Інструмент |
|---|---|
| Backend | Python 3.12, Django 6.0 |
| БД | PostgreSQL 18, psycopg 3 |
| Frontend | Bootstrap 5.3, Chart.js 4.4, Leaflet 1.9, FullCalendar 6.1 |
| Карти | OSRM (маршрутизація), CartoDB Voyager (тайли) |
| PDF | ReportLab + qrcode |
| Excel | openpyxl |
| Production | Gunicorn + WhiteNoise, Render Free |

## Як запустити локально

Потрібно: Python 3.12, PostgreSQL 18 з порожньою БД `transport_db`.

```bash
cd transport_app
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

pip install -r requirements.txt

copy .env.example .env          # Windows
# cp .env.example .env          # Linux/Mac
# відкрити .env і заповнити SECRET_KEY та DATABASE_PASSWORD

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Згенерувати `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Якщо PowerShell не дає кирилицю:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
```

Доступні адреси:
- `http://127.0.0.1:8000/` клієнтський сайт,
- `http://127.0.0.1:8000/manage/` диспетчерська (логін як superuser),
- `http://127.0.0.1:8000/admin/` Django admin.

## Демо-дані

Залити порожню БД даними для презентації (10 водіїв, 10 ТЗ, 17 маршрутів, ~1490 рейсів, ~23k замовлень, ~37k квитків):

```bash
python manage.py seed_demo_data --reset
python manage.py seed_bookings --reset
python manage.py seed_reviews
python manage.py seed_companies
python manage.py update_trip_statuses
python manage.py redistribute_order_dates
python manage.py fill_recent_bookings
python manage.py backfill_loyalty
```

Решта seed-команд описані у `apps/core/management/commands/` (вони мають короткі docstring у кожному файлі).

## Структура

```
config/                  settings.py, urls.py
apps/
  accounts/              User з ролями і бонусними балами
  customers/             корпоративні клієнти
  fleet/                 Vehicle + Driver
  routes/                Route, Stop, Trip
  orders/                Order, Ticket, PromoCode + signals
  reviews/               відгуки клієнтів
  documents/             PDF з QR (services.py)
  core/                  диспетчерська /manage/, middleware, audit log
  portal/                публічний сайт + booking_service.py + gps_simulator.py
templates/               шаблони
static/                  CSS, JS, картинки
```

## Деплой

Розгорнуто на Render Free плані з PostgreSQL у регіоні Frankfurt. Конфігурація у `render.yaml`.

Що зробити для самостійного деплою на Render:
1. Створити новий Web Service з GitHub-репо.
2. Прив'язати PostgreSQL-БД у тому самому регіоні (інакше внутрішній хост не резолвиться).
3. Render автоматично прочитає `render.yaml` і встановить env-змінні: `DEBUG=False`, `ALLOWED_HOSTS=.onrender.com`, `SECRET_KEY` (генерує сам), `DATABASE_URL` (з прив'язаної БД), `PYTHON_VERSION`.
4. У startCommand виконається `migrate` потім стартує gunicorn.

Render Free має обмеження: сервіс «засинає» після 15 хв бездіяльності (перший запит після сну ~30-60 сек), безкоштовна Postgres видаляється через 90 днів від створення.

## Безпека

Що зроблено для production:
- `select_for_update` на Trip і PromoCode у `booking_service.py` проти race condition коли два клієнти беруть одне останнє місце,
- IDOR-перевірки у `booking_done`, `booking_detail`, `cancel_booking`, PDF-видачі квитків,
- `staff_required` на усіх `/manage/` views, `@require_POST` на logout,
- `AUTH_PASSWORD_VALIDATORS` обмежують слабкі паролі (мін. 8 символів, не суцільні цифри),
- захист від open redirect через `url_has_allowed_host_and_scheme`,
- XLSX-injection захист у експортах через префікс апострофа,
- при `DEBUG=False` вмикаються `SECURE_SSL_REDIRECT`, `HSTS`, `SESSION_COOKIE_SECURE`, `X_FRAME_OPTIONS=DENY`.

## Автор

Калабішка Ярослав, 4 курс, спеціальність «Комп'ютерні науки», ДВНЗ УжНУ, 2026.
