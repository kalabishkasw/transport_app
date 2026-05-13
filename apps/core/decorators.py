"""
декоратори авторизації для диспетчерської панелі.

staff_required - заміна стандартного @login_required для views у /manage/.
допускає тільки користувачів з ролями адміністратор, диспетчер, бухгалтер
або з прапорцем is_staff.
доповнення: звичайні клієнти отримують Http404 (а не 403, щоб не розкривати сам факт існування адмін-панелі).
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import Http404


STAFF_ROLES = ('admin', 'dispatcher', 'accountant')


def is_staff_user(user) -> bool:
    """перевіряє чи користувач має право доступу до диспетчеської"""
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return getattr(user, 'role', None) in STAFF_ROLES


def staff_required(view_func):
    """
    декоратор: спочатку login_required, потім перевірка is_staff/role
    клієнтам показує 404, не 403 - щоб приховати наявність /manage/
    """
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_staff_user(request.user):
            raise Http404()
        return view_func(request, *args, **kwargs)
    return wrapper
