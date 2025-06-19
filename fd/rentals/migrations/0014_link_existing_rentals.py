from django.db import migrations
from datetime import datetime

def link_existing_rentals(apps, schema_editor):
    RentalApplication = apps.get_model('rentals', 'RentalApplication')
    Client = apps.get_model('rentals', 'Client')
    Calendar = apps.get_model('rentals', 'Calendar')

    # Process all rental applications
    for rental in RentalApplication.objects.all():
        # Create or get client
        client, created = Client.objects.get_or_create(
            phone_number=rental.phone_number,
            defaults={
                'full_name': rental.full_name
            }
        )
        
        # Link rental to client
        rental.client = client
        rental.save()

        # Create calendar event if it doesn't exist
        calendar_event, created = Calendar.objects.get_or_create(
            rental_application=rental,
            defaults={
                'transport': rental.transport,
                'title': f"Аренда: {rental.full_name}",
                'start': datetime.combine(rental.rental_start_date, datetime.min.time()),
                'end': datetime.combine(rental.rental_end_date, datetime.max.time()),
                'status': rental.status,
                'all_day': True
            }
        )

        # Update calendar event if it exists
        if not created:
            calendar_event.transport = rental.transport
            calendar_event.title = f"Аренда: {rental.full_name}"
            calendar_event.start = datetime.combine(rental.rental_start_date, datetime.min.time())
            calendar_event.end = datetime.combine(rental.rental_end_date, datetime.max.time())
            calendar_event.status = rental.status
            calendar_event.save()

def reverse_migration(apps, schema_editor):
    # No need to reverse this migration as it only links existing data
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('rentals', '0013_calendar'),
    ]

    operations = [
        migrations.RunPython(link_existing_rentals, reverse_migration),
    ] 