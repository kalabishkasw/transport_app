"""
сигнали модуля routes:
- скидаю кеш списку міст (_all_cities, _cities_with_country) при будь-якій
  зміні маршрутів або зупинок, інакше додане у admin місто зявляється на
  лендінгу і у формі пошуку аж через 10 хвилин (TTL кеша).
"""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Route, Stop


CITIES_CACHE_KEYS = [
    'portal_all_cities_v1',
    'portal_cities_with_country_v1_uk',
    'portal_cities_with_country_v1_en',
]


def _flush_cities_cache():
    """видаляю всі кеш-ключі повʼязані зі списком міст."""
    for key in CITIES_CACHE_KEYS:
        cache.delete(key)


@receiver(post_save, sender=Stop)
@receiver(post_delete, sender=Stop)
def invalidate_cities_on_stop_change(sender, **kwargs):
    _flush_cities_cache()


@receiver(post_save, sender=Route)
@receiver(post_delete, sender=Route)
def invalidate_cities_on_route_change(sender, **kwargs):
    _flush_cities_cache()
