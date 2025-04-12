# cinema_tickets/admin.py
from django.contrib import admin
from django.utils.html import format_html # Добавлен импорт
from .models import ФизическиеЛица, СеансыФильмов, МестаВЗале, КупленныеБилеты
from .utils import generate_ticket_pdf # Оставляем импорт

@admin.register(ФизическиеЛица)
class ФизическиеЛицаAdmin(admin.ModelAdmin):
    # <-- Добавляем email -->
    list_display = ('фамилия', 'имя', 'отчество', 'номер_телефона', 'email', 'дата_рождения')
    search_fields = ('фамилия', 'имя', 'номер_телефона', 'email') # <-- Добавляем email -->

@admin.register(СеансыФильмов)
class СеансыФильмовAdmin(admin.ModelAdmin):
    list_display = ('название_фильма', 'время_начала', 'время_окончания', 'продолжительность')
    list_filter = ('название_фильма', 'время_начала')
    search_fields = ('название_фильма',)

@admin.register(МестаВЗале)
class МестаВЗалеAdmin(admin.ModelAdmin):
    list_display = ('номер_места',)

@admin.register(КупленныеБилеты)
class КупленныеБилетыAdmin(admin.ModelAdmin):
    # <-- Добавляем email_получателя -->
    list_display = ('id', 'клиент', 'сеанс', 'место', 'дата_покупки', 'email_получателя', 'pdf_файл_link')
    list_filter = ('сеанс__название_фильма', 'сеанс__время_начала', 'дата_покупки', 'email_получателя')
    search_fields = ('клиент__фамилия', 'клиент__имя', 'сеанс__название_фильма', 'email_получателя')
    raw_id_fields = ('клиент', 'сеанс', 'место')
    # <-- Добавляем email_получателя в readonly, т.к. он задается при покупке -->
    readonly_fields = ('дата_покупки', 'pdf_файл', 'email_получателя',)

    def pdf_файл_link(self, obj):
        if obj.pdf_файл:
            return format_html('<a href="{}" target="_blank">Скачать/Посмотреть PDF</a>', obj.pdf_файл.url)
        return "Еще не сгенерирован"
    pdf_файл_link.short_description = "PDF Билет"

    # Метод save_model остается как был (генерирует PDF при сохранении в админке)
    # НЕ добавляем сюда отправку email, чтобы избежать случайных отправок из админки
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.pk:
            try:
                print(f"Пытаемся сгенерировать PDF для билета ID: {obj.pk} (из админки)")
                generate_ticket_pdf(obj) # Эта функция теперь будет включать QR/штрихкод
                print(f"PDF для билета ID: {obj.pk} успешно сгенерирован и сохранен (из админки).")
            except Exception as e:
                print(f"Ошибка генерации PDF для билета {obj.pk} через админку: {e}")
                from django.contrib import messages
                messages.error(request, f"Не удалось сгенерировать PDF для билета {obj.pk}: {e}")