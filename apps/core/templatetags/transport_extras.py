"""користувацькі шаблоні фільтри для проекту"""

from datetime import timedelta

from django import template


register = template.Library()


@register.filter(name='format_minutes')
def format_minutes(minutes):
    """
    форматує кількість хвилин у вигляд X год Y хв або Y хв
    """
    try:
        m = int(minutes)
    except (TypeError, ValueError):
        return ''
    if m < 60:
        return f'{m} хв'
    hours = m // 60
    mins = m % 60
    return f'{hours} год {mins:02d} хв'


@register.filter(name='add_minutes')
def add_minutes(value, minutes):
    """
    додає вказану кількість хвилин до datetime або date.

    використання у шаблоні:
        {{ trip.departure_at|add_minutes:stop.departure_offset_minutes|date:"H:i" }}
    """
    if value is None or minutes in (None, ''):
        return value
    try:
        m = int(minutes)
    except (TypeError, ValueError):
        return value
    try:
        return value + timedelta(minutes=m)
    except TypeError:
        return value
