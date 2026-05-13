"""
Налаштування Django-проекту для веб-застосунку міжнародної транспортної компанії.

Чутливі параметри читаються з .env файлу (див. .env.example).
Для production обовязково встановіть DEBUG=False, ALLOWED_HOSTS, SECRET_KEY.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Завантаження змінних з .env
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    """Прочитати булеву змінну з .env."""
    return os.getenv(name, str(default)).lower() in ('1', 'true', 'yes', 'on')


# ----------------------- Безпека -----------------------

DEBUG = env_bool('DEBUG', True)

SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        # Безпечний дефолт ТІЛЬКИ для розробки
        SECRET_KEY = 'unsafe-dev-only-{}'.format(os.urandom(16).hex())
    else:
        raise ImproperlyConfigured(
            'SECRET_KEY не задано. Встановіть його у .env перед запуском у production.'
        )

# ALLOWED_HOSTS читаємо з env через кому: "example.com,www.example.com"
# для Render підтримуємо ".onrender.com" як wildcard
_default_hosts = 'localhost,127.0.0.1,0.0.0.0'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', _default_hosts).split(',') if h.strip()]

# на Render додаємо власне ім'я сервісу до ALLOWED_HOSTS (передається у env RENDER_EXTERNAL_HOSTNAME)
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


# ----------------------- Застосунки -----------------------

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


# ----------------------- Middleware -----------------------

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


# ----------------------- База даних -----------------------
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


# ----------------------- Кеш -----------------------
# Локальний LocMemCache - кожен процес тримає окремий кеш. Цього достатньо
# для розробки. У production з кількома gunicorn-воркерами краще Redis,
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


# ----------------------- Валідація паролів -----------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ----------------------- Локалізація -----------------------

LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True


# ----------------------- Статика та медіа -----------------------

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


# ----------------------- Інше -----------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/admin/login/'


# ----------------------- Email -----------------------
# Бекенд читається з env. У розробці типово 'console' (листи у термінал),
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


# ----------------------- Бізнес-константи: бонусна програма -----------------------
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


# ----------------------- Logging -----------------------
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
