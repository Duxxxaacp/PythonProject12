# cinema_tickets/management/commands/populate_seats.py
from django.core.management.base import BaseCommand
from cinema_tickets.models import МестаВЗале

class Command(BaseCommand):
    help = 'Создает места в зале от 1 до 100, если они еще не существуют'

    def handle(self, *args, **options):
        created_count = 0
        for i in range(1, 101):
            seat, created = МестаВЗале.objects.get_or_create(номер_места=i)
            if created:
                created_count += 1
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Успешно создано {created_count} новых мест.'))
        else:
             self.stdout.write(self.style.WARNING('Новых мест не создано (вероятно, уже существуют).'))
        total_seats = МестаВЗале.objects.count()
        self.stdout.write(f'Всего мест в базе: {total_seats}')