"""
налаштування Django-проекту для веб-застосунку міжнародної транспортної компанії.

чутливі параметри читаються з .env файлу (див. .env.example).
для production DEBUG=False, ALLOWED_HOSTS, SECRET_KEY.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# завантаження змінних з .env
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    """прочитати булеву змінну з .env."""
    return os.getenv(name, str(default)).lower() in ('1', 'true', 'yes', 'on')


# безпека

DEBUG = env_bool('DEBUG', True)

SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        # безпечний дефолт ТІЛЬКИ для розробки
        SECRET_KEY = 'unsafe-dev-only-{}'.format(os.urandom(16).hex())
    else:
        raise ImproperlyConfigured(
            'SECRET_KEY не задано. Встановіть його у .env перед запуском у production.'
        )

# ALLOWED_HOSTS читаю з env через кому: "example.com,www.example.com"
# для Render підтримуємо ".onrender.com" як wildcard
_default_hosts = 'localhost,127.0.0.1,0.0.0.0'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', _default_hosts).split(',') if h.strip()]

# на Render додав власне ім'я сервісу до ALLOWED_HOSTS (передається у env RENDER_EXTERNAL_HOSTNAME)
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Production-only заходи безпеки
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))  # 1 рік
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = 'same-origin'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# застосунки

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'django_bootstrap5',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.customers',
    'apps.fleet',
    'apps.routes',
    'apps.orders',
    'apps.documents',
    'apps.core',
    'apps.portal',
    'apps.reviews',
]

AUTH_USER_MODEL = 'accounts.User'

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# Middleware

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # whitenoise роздає static-файли у production без nginx
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.CurrentUserMiddleware',
    # раз на 5 хвилин переводить минулі рейси у "Завершено", поточні у "У дорозі"
    'apps.core.middleware.AutoUpdateTripStatusMiddleware',
]

# CSP middleware додаємо тільки якщо пакет встановлено і не у DEBUG.
# у DEBUG CSP заважає django-debug-toolbar та live-reload скриптам.
try:
    import csp  # noqa: F401
    if not DEBUG:
        MIDDLEWARE.append('csp.middleware.CSPMiddleware')
except ImportError:
    pass

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.portal.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


#  база даних
# у production Render передає DATABASE_URL з підключеної postgres-бази.
# локально читаємо окремі параметри з .env (DATABASE_NAME, _USER тощо).

import dj_database_url

DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=not DEBUG),
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME', 'transport_db'),
            'USER': os.getenv('DATABASE_USER', 'postgres'),
            'PASSWORD': os.getenv('DATABASE_PASSWORD', ''),
            'HOST': os.getenv('DATABASE_HOST', 'localhost'),
            'PORT': os.getenv('DATABASE_PORT', '5432'),
        }
    }


#  Кеш
# У production з кількома gunicorn-воркерами краще Redis,
# щоб middleware-локи (AutoUpdateTripStatusMiddleware) працювали глобально.
CACHES = {
    'default': {
        'BACKEND': os.getenv(
            'CACHE_BACKEND',
            'django.core.cache.backends.locmem.LocMemCache',
        ),
        'LOCATION': os.getenv('CACHE_LOCATION', 'transport-app-default'),
    }
}


# валідація паролів

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


#  Локалізація

LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True


#  Статика та медіа

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# whitenoise: компресія і кешування static-файлів у production
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


#  Інше

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/account/'
LOGOUT_REDIRECT_URL = '/'


#  Email
# бекенд читається з env. У розробці типово 'console' (листи у термінал),
# у production - 'smtp' з реальними реквізитами.

EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    'TransAuto Travel <noreply@transauto.travel>',
)
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@transauto.travel')


#  бізнес-константи: бонусна програма
# 1 EUR суми завершеного замовлення = 1 бал лояльності.
# Бали можна списати при оплаті, але не більше LOYALTY_MAX_REDEEM_RATIO * total_price.

from decimal import Decimal as _Decimal

LOYALTY_POINTS_PER_EUR = 1
LOYALTY_MAX_REDEEM_RATIO = _Decimal('0.5')  # макс. 50% від суми замовлення балами
LOYALTY_LEVELS = [
    # (назва, мін. кількість балів, hex-колір градієнту картки)
    ('Базовий',     0,   '#64748b'),
    ('Срібний',     100, '#94a3b8'),
    ('Золотий',     250, '#f59e0b'),
    ('Платиновий',  500, '#0ea5e9'),
]


# бізнес-константи: бронювання
# за скільки годин до рейсу клієнт ще може скасувати замовлення
BOOKING_CANCEL_HOURS_BEFORE_TRIP = int(os.getenv('BOOKING_CANCEL_HOURS_BEFORE_TRIP', '24'))

# фіксований курс EUR -> UAH. якщо задано не порожній - використовується замість
# курсу НБУ. для дипломної демонстрації гарантує що ціна не змінюється між
# рестартами runserver і між різними сторінками. рекомендую '51.5' як середнє.
EUR_TO_UAH_FIXED = os.getenv('EUR_TO_UAH_FIXED', '51.5')


# маркетингові статистики на лендінгу.
# реальна кількість квитків у базі множиться на ці значення,
# щоб не показувати голу цифру для свіжо-заповненої демо-БД.
# для production бажано виставити LANDING_PASSENGER_MULTIPLIER=1.
LANDING_PASSENGER_MULTIPLIER = int(os.getenv('LANDING_PASSENGER_MULTIPLIER', '17'))
LANDING_PASSENGER_FLOOR = int(os.getenv('LANDING_PASSENGER_FLOOR', '12500'))
LANDING_TRIPS_PER_MONTH_FLOOR = int(os.getenv('LANDING_TRIPS_PER_MONTH_FLOOR', '120'))
LANDING_ROUTES_FLOOR = int(os.getenv('LANDING_ROUTES_FLOOR', '25'))
LANDING_CITIES_FLOOR = int(os.getenv('LANDING_CITIES_FLOOR', '40'))


# Sentry: моніторинг помилок у production.
# ініціалізую тільки якщо у env є SENTRY_DSN (інакше працює без моніторингу).
# у DEBUG не активую, щоб локальні помилки не летіли у трекер.
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN and not DEBUG:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            # відсоток запитів які трасуються (performance monitoring).
            # 0 = тільки помилки, без перформанс-трейсів.
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0')),
            # надсилати PII (IP, headers) у Sentry. за замовчуванням ні.
            send_default_pii=env_bool('SENTRY_SEND_PII', False),
            environment=os.getenv('SENTRY_ENVIRONMENT', 'production'),
        )
    except ImportError:
        # sentry-sdk не встановлено - тихо ігнорую (для випадків коли
        # SENTRY_DSN випадково попав у .env при відсутності пакета).
        pass


# Content Security Policy.
# дозволяю CDN-домени які реально використовуються у шаблонах:
# - cdn.jsdelivr.net: bootstrap, chart.js, fullcalendar, flatpickr, bootstrap-icons
# - unpkg.com: leaflet
# - fonts.googleapis.com, fonts.gstatic.com: Inter font
# - flagcdn.com: прапори у мова-перемикачі
# - basemaps.cartocdn.com: tiles карти
# - router.project-osrm.org: OSRM API для маршрутизації
# - images.unsplash.com: hero-картинки на лендінгу
# - bank.gov.ua: курс НБУ (з боку клієнта не використовується, але про всяк)
# - api.open-meteo.com: погода
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",  # inline-скрипти у шаблонах. в ідеалі винести у .js файли.
    'https://cdn.jsdelivr.net',
    'https://unpkg.com',
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",  # inline-стилі у багатьох шаблонах
    'https://cdn.jsdelivr.net',
    'https://unpkg.com',
    'https://fonts.googleapis.com',
)
CSP_FONT_SRC = (
    "'self'",
    'https://fonts.gstatic.com',
    'https://cdn.jsdelivr.net',
    'data:',
)
CSP_IMG_SRC = (
    "'self'",
    'data:',
    'https://cdn.jsdelivr.net',
    'https://flagcdn.com',
    'https://basemaps.cartocdn.com',
    'https://*.tile.openstreetmap.org',
    'https://images.unsplash.com',
    'https://unpkg.com',
)
CSP_CONNECT_SRC = (
    "'self'",
    'https://router.project-osrm.org',
    'https://api.open-meteo.com',
)
CSP_FRAME_ANCESTORS = ("'none'",)


#  Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
