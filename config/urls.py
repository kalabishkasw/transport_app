"""
Кореневий URL-маршрутизатор проекту.
- /admin/  - стандартна Django admin для CRUD
- /docs/   - PDF-документи (квиток, посадковий лист)
- /manage/ - диспетчерська панель (apps.core)
- /       - публічний клієнтський сайт (apps.portal)
У DEBUG-режимі додатково роздає статику і медіа через staticfiles_urlpatterns.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path


urlpatterns = [
    path('admin/', admin.site.urls),
    path('docs/', include('apps.documents.urls')),
    path('manage/', include('apps.core.urls')),
    path('', include('apps.portal.urls')),
]

if settings.DEBUG:
    # Медіа-файли (завантажені користувачами): фото авто, аватари тощо.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Статика: офіційний хелпер Django, який роздає файли з усіх STATICFILES_DIRS
    # та з app/static/ підпапок усіх застосунків. Працює тільки у DEBUG-режимі,
    # тож перед deploy у продакшн запускайте collectstatic.
    urlpatterns += staticfiles_urlpatterns()
