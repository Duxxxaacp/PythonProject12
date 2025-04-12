# cinema_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('cinema_tickets.urls', namespace='cinema_tickets')), # Подключаем URL приложения
]

# Добавляем обработку медиа файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Для статики (шрифта), если STATIC_URL/ROOT настроены
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)