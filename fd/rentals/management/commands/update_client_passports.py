from django.core.management.base import BaseCommand
from rentals.models import Client, RentalApplication


class Command(BaseCommand):
    help = 'Обновляет паспортные данные клиентов из заявок на аренду'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет обновлено без внесения изменений',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно обновить все паспортные данные (даже если они уже заполнены)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        clients = Client.objects.all()
        updated_count = 0
        total_clients = clients.count()
        
        self.stdout.write(f"Найдено клиентов: {total_clients}")
        
        for client in clients:
            # Получаем все заявки этого клиента с паспортными данными
            rentals_with_passport = RentalApplication.objects.filter(
                client=client,
                passport_number__isnull=False
            ).exclude(passport_number='')
            
            if rentals_with_passport.exists():
                # Берем данные из первой заявки с паспортными данными
                rental = rentals_with_passport.first()
                
                # Проверяем, нужно ли обновлять данные
                needs_update = False
                update_fields = []
                
                if force or (rental.passport_number and not client.passport_number):
                    if client.passport_number != rental.passport_number:
                        update_fields.append(f"passport_number: '{client.passport_number}' -> '{rental.passport_number}'")
                        needs_update = True
                
                if force or (rental.passport_issued_by and not client.passport_issued_by):
                    if client.passport_issued_by != rental.passport_issued_by:
                        update_fields.append(f"passport_issued_by: '{client.passport_issued_by}' -> '{rental.passport_issued_by}'")
                        needs_update = True
                
                if force or (rental.passport_issue_date and not client.passport_issue_date):
                    if client.passport_issue_date != rental.passport_issue_date:
                        update_fields.append(f"passport_issue_date: {client.passport_issue_date} -> {rental.passport_issue_date}")
                        needs_update = True
                
                if needs_update:
                    if not dry_run:
                        # Обновляем паспортные данные клиента
                        if rental.passport_number and (force or not client.passport_number):
                            client.passport_number = rental.passport_number
                        if rental.passport_issued_by and (force or not client.passport_issued_by):
                            client.passport_issued_by = rental.passport_issued_by
                        if rental.passport_issue_date and (force or not client.passport_issue_date):
                            client.passport_issue_date = rental.passport_issue_date
                        
                        client.save()
                        updated_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Клиент {client.full_name} ({client.phone_number}): {' | '.join(update_fields)}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Клиент {client.full_name} ({client.phone_number}): паспортные данные уже заполнены"
                        )
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Клиент {client.full_name} ({client.phone_number}): нет заявок с паспортными данными"
                    )
                )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY RUN: Будет обновлено {updated_count} клиентов из {total_clients}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Обновлено {updated_count} клиентов из {total_clients}"
                )
            ) 