"""
apps orders не має власних views.
робота з замовленнями і квитками:
- apps.portal.views для клієнтів (бронювання, перегляд своїх замовлень);
- apps.core.views для диспетчера (списки, деталі, експорт).
"""
from django.shortcuts import render
