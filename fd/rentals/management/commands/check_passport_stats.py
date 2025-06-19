from django.core.management.base import BaseCommand
from rentals.models import Client, RentalApplication


class Command(BaseCommand):
    help = 'Показывает статистику паспортных данных клиентов'

    def handle(self, *args, **options):
        total_clients = Client.objects.count()
        clients_with_passport = Client.objects.filter(passport_number__isnull=False).exclude(passport_number='').count()
        clients_without_passport = total_clients - clients_with_passport
        
        total_rentals = RentalApplication.objects.count()
        rentals_with_passport = RentalApplication.objects.filter(passport_number__isnull=False).exclude(passport_number='').count()
        rentals_without_passport = total_rentals - rentals_with_passport
        
        self.stdout.write("=" * 50)
        self.stdout.write("СТАТИСТИКА ПАСПОРТНЫХ ДАННЫХ")
        self.stdout.write("=" * 50)
        
        self.stdout.write(f"Клиентов всего: {total_clients}")
        self.stdout.write(f"  - С паспортными данными: {clients_with_passport}")
        self.stdout.write(f"  - Без паспортных данных: {clients_without_passport}")
        
        if total_clients > 0:
            percentage = (clients_with_passport / total_clients) * 100
            self.stdout.write(f"  - Процент заполненности: {percentage:.1f}%")
        
        self.stdout.write("")
        self.stdout.write(f"Заявок всего: {total_rentals}")
        self.stdout.write(f"  - С паспортными данными: {rentals_with_passport}")
        self.stdout.write(f"  - Без паспортных данных: {rentals_without_passport}")
        
        if total_rentals > 0:
            percentage = (rentals_with_passport / total_rentals) * 100
            self.stdout.write(f"  - Процент заполненности: {percentage:.1f}%")
        
        self.stdout.write("")
        self.stdout.write("КЛИЕНТЫ С ПАСПОРТНЫМИ ДАННЫМИ:")
        self.stdout.write("-" * 30)
        
        clients_with_data = Client.objects.filter(passport_number__isnull=False).exclude(passport_number='')
        for client in clients_with_data:
            self.stdout.write(f"  {client.full_name} ({client.phone_number})")
            self.stdout.write(f"    Паспорт: {client.passport_number}")
            if client.passport_issued_by:
                self.stdout.write(f"    Выдан: {client.passport_issued_by}")
            if client.passport_issue_date:
                self.stdout.write(f"    Дата выдачи: {client.passport_issue_date}")
            self.stdout.write("")
        
        if clients_with_data.count() == 0:
            self.stdout.write("  Нет клиентов с паспортными данными")
        
        self.stdout.write("=" * 50) 