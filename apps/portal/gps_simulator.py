"""
симулятор gps-позиції автобуса. на основі часу від відправлення інтерполюю
поточну позицію між зупинками маршруту.

у реальній системі тут була б інтеграція з gps-трекером (наприклад, через
протокол wialon або власний сервер прийому позицій). для дипломної демо
імітую рух по маршруту з використанням реальних координат зупинок.

підтримує "demo-режим": якщо рейс ще не розпочався, можна штучно запустити
симуляцію, щоб одразу побачити рух автобуса (час прискорений).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Optional

from django.utils import timezone


@dataclass
class GpsPosition:
    lat: float
    lng: float
    speed_kmh: float
    progress_percent: float
    nearest_stop_name: str
    nearest_stop_index: int
    next_stop_name: str
    eta_minutes: int
    is_finished: bool
    minutes_since_departure: int
    # Прогрес всередині поточного сегмента (від зупинки K до K+1), 0..1.
    # Потрібен клієнту, щоб точно позиціонувати автобус на OSRM-полілінії
    # саме між цими зупинками, а не за загальним відсотком часу.
    segment_t: float = 0.0


def _haversine_km(p1, p2):
    """Відстань між двома координатами у км (формула гаверсинуса)."""
    lat1, lon1 = radians(p1[0]), radians(p1[1])
    lat2, lon2 = radians(p2[0]), radians(p2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(h))


def _interpolate(p1, p2, t: float):
    """Лінійна інтерполяція між двома точками. t у [0, 1]."""
    return (
        p1[0] + (p2[0] - p1[0]) * t,
        p1[1] + (p2[1] - p1[1]) * t,
    )


def simulate_position(trip, demo_mode: bool = False) -> Optional[GpsPosition]:
    """
    Повертає псевдо-GPS позицію автобуса для рейсу.

    Параметри
    ---------
    trip : Trip
        Об'єкт рейсу. Має мати маршрут зі зупинками з координатами.
    demo_mode : bool
        Якщо True, рейс програється прискорено (1 хв реального часу = 30 хв
        поїздки). Корисно для демо коли рейс заплановано на майбутнє.

    Повертає
    --------
    GpsPosition або None
        None - коли рейс скасовано або у маршруті < 2 зупинок з координатами.
    """
    if trip.status == 'cancelled':
        return None

    stops = list(
        trip.route.stops
        .filter(latitude__isnull=False, longitude__isnull=False)
        .order_by('order')
    )
    if len(stops) < 2:
        return None

    now = timezone.now()
    duration = trip.route.duration_minutes or 60
    total_minutes = max(stops[-1].departure_offset_minutes, duration)

    if demo_mode:
        # Прискорене програвання: 1 секунда реального часу = 10 хвилин поїздки.
        # Тобто 6-годинна поїздка програється за 36 секунд, 10-годинна за 60 сек.
        # Цикл повторюється кожні total_minutes/10 секунд.
        seconds_now = int(now.timestamp())
        delta = float((seconds_now * 10) % total_minutes)
    else:
        delta = (now - trip.departure_at).total_seconds() / 60.0

    # Рейс ще не почався (тільки у звичайному режимі).
    if not demo_mode and delta < 0:
        return None

    if delta >= total_minutes:
        # Поїздка завершена.
        last = stops[-1]
        return GpsPosition(
            lat=float(last.latitude),
            lng=float(last.longitude),
            speed_kmh=0.0,
            progress_percent=100.0,
            nearest_stop_name=last.city,
            nearest_stop_index=len(stops) - 1,
            next_stop_name='',
            eta_minutes=0,
            is_finished=True,
            minutes_since_departure=int(delta),
        )

    # Загальна довжина маршруту по прямих (для базової швидкості).
    # Реальна дорожна відстань більша на ~30%, тому коректуємо.
    total_route_km = sum(
        _haversine_km(
            (float(stops[i].latitude), float(stops[i].longitude)),
            (float(stops[i + 1].latitude), float(stops[i + 1].longitude)),
        )
        for i in range(len(stops) - 1)
    ) * 1.3
    # Базова крейсерська швидкість автобуса для цього маршруту:
    # довжина у км / тривалість у годинах. Зазвичай 50-70 км/год.
    base_speed = (total_route_km / (total_minutes / 60)) if total_minutes > 0 else 60

    # Знаходимо два сусідні стопи між якими зараз авто.
    for i in range(len(stops) - 1):
        s_curr = stops[i]
        s_next = stops[i + 1]
        t_curr = s_curr.departure_offset_minutes
        t_next = s_next.departure_offset_minutes if s_next.departure_offset_minutes > t_curr else (
            s_next.arrival_offset_minutes
        )
        if t_next <= t_curr:
            # Розподіляємо рівномірно якщо немає offset-ів
            t_next = t_curr + max(1, total_minutes // max(1, len(stops) - 1))

        if t_curr <= delta <= t_next:
            segment_duration = max(1, t_next - t_curr)
            t = (delta - t_curr) / segment_duration
            lat, lng = _interpolate(
                (float(s_curr.latitude), float(s_curr.longitude)),
                (float(s_next.latitude), float(s_next.longitude)),
                t,
            )

            # Реалістичний розрахунок швидкості замість простої "відстань/час".
            # Беремо базову крейсерську швидкість маршруту і модифікуємо її залежно
            # від ситуації:
            #  - коли під'їжджаємо/від'їжджаємо від зупинки (близько до меж сегмента) -
            #    швидкість падає (гальмування/розгін);
            #  - короткі сегменти між близькими містами вважаємо "повільнішими" (місто);
            #  - для деяких параметрів додаємо невеликий шум для природнього вигляду.
            import random
            from math import sin, pi

            segment_distance_km = _haversine_km(
                (float(s_curr.latitude), float(s_curr.longitude)),
                (float(s_next.latitude), float(s_next.longitude)),
            ) * 1.3

            # Чи це "повільний" сегмент: короткий (<20км) - типу місто/прикордоння
            is_slow_segment = segment_distance_km < 20
            target_speed = base_speed * (0.6 if is_slow_segment else 1.0)

            # Профіль розгону/гальмування: швидкість максимальна посередині сегмента
            # і знижується ближче до зупинок. Використовуємо синус для плавності.
            acceleration_factor = sin(t * pi)  # 0 -> 1 -> 0 від t=0 до t=1
            # Біля зупинки (t<0.05 або t>0.95) швидкість майже нульова.
            if t < 0.03 or t > 0.97:
                speed = random.uniform(0, 10)  # стоїть на зупинці
            elif t < 0.1:
                speed = target_speed * acceleration_factor * random.uniform(0.4, 0.6)  # розгін
            elif t > 0.9:
                speed = target_speed * acceleration_factor * random.uniform(0.4, 0.6)  # гальмування
            else:
                # Крейсерський режим: ціль ± 15% шуму
                speed = target_speed * random.uniform(0.85, 1.15)

            # Обмежуємо межі: автобус не їде швидше за 100 км/год і не від'ємно.
            speed = max(0, min(100, speed))

            return GpsPosition(
                lat=lat,
                lng=lng,
                speed_kmh=round(speed, 1),
                progress_percent=round((delta / total_minutes) * 100, 1),
                nearest_stop_name=s_curr.city,
                nearest_stop_index=i,
                next_stop_name=s_next.city,
                eta_minutes=int(t_next - delta),
                is_finished=False,
                minutes_since_departure=int(delta),
                segment_t=round(t, 4),
            )

    # Якщо delta між зупинок не знайдено (не повинно статись), повертаємо першу.
    first = stops[0]
    return GpsPosition(
        lat=float(first.latitude),
        lng=float(first.longitude),
        speed_kmh=0.0,
        progress_percent=0.0,
        nearest_stop_name=first.city,
        nearest_stop_index=0,
        next_stop_name=stops[1].city if len(stops) > 1 else '',
        eta_minutes=int(total_minutes // max(1, len(stops) - 1)),
        is_finished=False,
        minutes_since_departure=0,
    )
