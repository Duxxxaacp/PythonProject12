# cinema_tickets/urls.py
from django.urls import path
from . import views

app_name = 'cinema_tickets' # Пространство имен

urlpatterns = [
    # <<<--- Добавьте этот маршрут --->>>
    path('', views.home_view, name='home'), # Пустой путь для главной страницы

    # URL для "покупки" билета (принимает POST)
    path('purchase/', views.purchase_ticket_view, name='purchase_ticket'),

    # URL для API получения PDF
    path('api/tickets/<int:ticket_id>/pdf/', views.get_ticket_pdf_api, name='get_ticket_pdf'),
]