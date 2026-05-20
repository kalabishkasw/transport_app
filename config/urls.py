"""
кореневий URL-маршрутизатор проекту.
- /admin/  - стандартна Django admin для CRUD
- /docs/   - PDF-документи (квиток, посадковий лист)
- /manage/ - диспетчерська панель (apps.core)
- /healthz/- health-чек для load-balancer / monitoring (200 OK без БД)
- /       - публічний клієнтський сайт (apps.portal)
У DEBUG-режимі додатково роздає статику і медіа через staticfiles_urlpatterns.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import HttpResponse
from django.urls import include, path


def healthz(request):
    """найдешевший можливий health-чек: 200 OK з plain-текстом 'ok'.
    не звертається ні до БД, ні до кешу - щоб load-balancer не отримав
    false-negative при тимчасових проблемах з постгресом. для глибокої
    перевірки (БД + кеш) можна додати окремий /readyz/."""
    return HttpResponse('ok', content_type='text/plain')


urlpatterns = [
    path('healthz/', healthz, name='healthz'),
    path('admin/', admin.site.urls),
    path('docs/', include('apps.documents.urls')),
    path('manage/', include('apps.core.urls')),
    path('', include('apps.portal.urls')),
]

if settings.DEBUG:
    # медіа-файли (завантажені користувачами): фото авто, аватари тощо.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # статика: офіційний хелпер Django, який роздає файли з усіх STATICFILES_DIRS
    # та з app/static/ підпапок усіх застосунків. Працює тільки у DEBUG-режимі,
    # тож перед deploy у продакшн запускайте collectstatic.
    urlpatterns += staticfiles_urlpatterns()
