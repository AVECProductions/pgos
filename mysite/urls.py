from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from decouple import config

urlpatterns = [
    # Admin URL with custom path from settings
    path(f'{settings.ADMIN_URL}/', admin.site.urls),
    
    # Include all URLs from main app
    path('', include('main.urls')),  # This is important!
    
    # Auth URLs
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    
    # Media files in development
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
]