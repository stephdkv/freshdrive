from django.db import migrations

def update_client_passport_data(apps, schema_editor):
    Client = apps.get_model('rentals', 'Client')
    RentalApplication = apps.get_model('rentals', 'RentalApplication')
    
    # Получаем всех клиентов
    clients = Client.objects.all()
    
    for client in clients:
        # Получаем все заявки этого клиента с паспортными данными
        rentals_with_passport = RentalApplication.objects.filter(
            client=client,
            passport_number__isnull=False
        ).exclude(passport_number='')
        
        if rentals_with_passport.exists():
            # Берем данные из первой заявки с паспортными данными
            rental = rentals_with_passport.first()
            
            # Обновляем паспортные данные клиента
            if rental.passport_number and not client.passport_number:
                client.passport_number = rental.passport_number
            if rental.passport_issued_by and not client.passport_issued_by:
                client.passport_issued_by = rental.passport_issued_by
            if rental.passport_issue_date and not client.passport_issue_date:
                client.passport_issue_date = rental.passport_issue_date
            
            client.save()

def reverse_migration(apps, schema_editor):
    # Очищаем паспортные данные клиентов (опционально)
    Client = apps.get_model('rentals', 'Client')
    Client.objects.update(
        passport_number='',
        passport_issued_by='',
        passport_issue_date=None
    )

class Migration(migrations.Migration):
    dependencies = [
        ('rentals', '0016_client_passport_issue_date_client_passport_issued_by_and_more'),
    ]

    operations = [
        migrations.RunPython(update_client_passport_data, reverse_migration),
    ] 