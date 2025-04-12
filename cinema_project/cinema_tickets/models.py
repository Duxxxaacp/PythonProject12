# cinema_tickets/models.py
from django.db import models
from django.core.exceptions import ValidationError
from datetime import timedelta

class ФизическиеЛица(models.Model):
    фамилия = models.CharField("Фамилия", max_length=100)
    имя = models.CharField("Имя", max_length=100)
    отчество = models.CharField("Отчество", max_length=100, blank=True, null=True)
    номер_телефона = models.CharField("Номер телефона", max_length=20, unique=True)
    дата_рождения = models.DateField("Дата рождения")
    # <-- Новое поле -->
    email = models.EmailField("Email", max_length=254, blank=True, null=True, unique=True) # Добавим уникальность для email

    def __str__(self):
        return f"{self.фамилия} {self.имя} {self.отчество or ''}".strip()

    def get_full_name(self):
        return f"{self.фамилия} {self.имя} {self.отчество or ''}".strip()

    class Meta:
        verbose_name = "Физическое лицо"
        verbose_name_plural = "Физические лица"
        ordering = ['фамилия', 'имя']

class СеансыФильмов(models.Model):
    название_фильма = models.CharField("Название фильма", max_length=200)
    время_начала = models.DateTimeField("Время начала")
    время_окончания = models.DateTimeField("Время окончания")

    @property
    def продолжительность(self):
        if self.время_начала and self.время_окончания:
            duration = self.время_окончания - self.время_начала
            # Форматирование в "X часов Y минут"
            total_minutes = int(duration.total_seconds() / 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            parts = []
            if hours > 0:
                parts.append(f"{hours} ч.")
            if minutes > 0:
                 parts.append(f"{minutes} мин.")
            return " ".join(parts) if parts else "0 мин."
        return None

    def clean(self):
        if self.время_начала and self.время_окончания and self.время_окончания <= self.время_начала:
            raise ValidationError("Время окончания должно быть позже времени начала.")

    def __str__(self):
        return f"{self.название_фильма} ({self.время_начала.strftime('%d.%m.%Y %H:%M')})"

    class Meta:
        verbose_name = "Сеанс фильма"
        verbose_name_plural = "Сеансы фильмов"
        ordering = ['время_начала']

class МестаВЗале(models.Model):
    номер_места = models.PositiveIntegerField("Номер места", unique=True)

    def __str__(self):
        return f"Место №{self.номер_места}"

    class Meta:
        verbose_name = "Место в зале"
        verbose_name_plural = "Места в зале"
        ordering = ['номер_места']

class КупленныеБилеты(models.Model):
    клиент = models.ForeignKey(ФизическиеЛица, on_delete=models.PROTECT, verbose_name="Клиент")
    сеанс = models.ForeignKey(СеансыФильмов, on_delete=models.PROTECT, verbose_name="Сеанс")
    место = models.ForeignKey(МестаВЗале, on_delete=models.PROTECT, verbose_name="Место")
    дата_покупки = models.DateTimeField("Дата покупки", auto_now_add=True)
    pdf_файл = models.FileField("PDF Билет", upload_to='tickets/', blank=True, null=True)
    # <-- Новое поле для хранения email, на который был отправлен билет -->
    # Это полезно, т.к. email клиента в ФизическиеЛица может измениться позже
    email_получателя = models.EmailField("Email получателя при покупке", blank=True, null=True)

    def __str__(self):
        return f"Билет №{self.id} - {self.клиент} на {self.сеанс}"

    class Meta:
        verbose_name = "Купленный билет"
        verbose_name_plural = "Купленные билеты"
        unique_together = ('сеанс', 'место')
        ordering = ['-дата_покупки']