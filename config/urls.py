"""GAAM Kindergarten URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import homepage


urlpatterns = [
    path('', homepage, name='homepage'),  # ⭐ یہ لائن اض
    path('admin/', admin.site.urls),
    path('', include('chat.urls')),
    path('core/', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
