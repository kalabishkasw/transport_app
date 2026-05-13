#!/usr/bin/env bash
# скрипт build-step для render
# виконується при кожному deploy: ставить залежності, збирає статику, мігрує бд
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input
