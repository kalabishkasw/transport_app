"""
apps accounts не має власних views.
логін/реєстрація клієнтів - у apps.portal.views, авторизація
персоналу - через стандартний django admin (/admin/login/).
"""
from django.shortcuts import render
