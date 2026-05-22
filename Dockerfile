# образ для веб-застосунку TransAuto Travel.
# базую на офіційному slim-образі python 3.12 (як локально і на Render).

FROM python:3.12-slim

# деякі бінарні залежності для psycopg та pillow.
# libpq-dev: PostgreSQL клієнт; gcc/python3-dev: для збірки колес;
# libjpeg/zlib: для pillow (обробка зображень);
# fonts-dejavu-core: шрифти DejaVu для генерації PDF з кирилицею (reportlab).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# не буферизую stdout щоб логи django одразу йшли у docker logs
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

# спершу копіюю тільки requirements.txt і встановлюю залежності.
# докер кешує цей шар, тож при зміні коду pip install не виконується знову.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# тепер копіюю весь код проекту
COPY . .

# збираю static-файли (для WhiteNoise з ManifestStorage).
# DJANGO_SETTINGS_MODULE заданий через docker-compose.yml.
RUN python manage.py collectstatic --no-input --clear || echo "static skipped"

# порт за яким буде доступний gunicorn у контейнері
EXPOSE 8000

# команда запуску: міграції + gunicorn. так само як на Render.
CMD ["sh", "-c", "python manage.py migrate --no-input && gunicorn config.wsgi:application --workers 2 --threads 2 --timeout 120 --bind 0.0.0.0:8000 --access-logfile - --error-logfile -"]
