from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rentals.models import Transport, RentalApplication

class Command(BaseCommand):
    help = 'Creates default user groups and sets up their permissions'

    def handle(self, *args, **options):
        # Создаем группу менеджеров
        manager_group, created = Group.objects.get_or_create(name='Manager')
        if created:
            self.stdout.write(self.style.SUCCESS('Successfully created Manager group'))
        else:
            self.stdout.write('Manager group already exists')

        # Получаем content types для наших моделей
        transport_ct = ContentType.objects.get_for_model(Transport)
        rental_ct = ContentType.objects.get_for_model(RentalApplication)

        # Определяем права для менеджеров
        manager_permissions = [
            # Права на просмотр транспорта
            Permission.objects.get(content_type=transport_ct, codename='view_transport'),
            
            # Права на работу с заявками
            Permission.objects.get(content_type=rental_ct, codename='view_rentalapplication'),
            Permission.objects.get(content_type=rental_ct, codename='add_rentalapplication'),
            Permission.objects.get(content_type=rental_ct, codename='change_rentalapplication'),
        ]

        # Назначаем права группе менеджеров
        manager_group.permissions.set(manager_permissions)
        self.stdout.write(self.style.SUCCESS('Successfully set up Manager group permissions'))

        # Выводим информацию о правах
        self.stdout.write('\nManager group permissions:')
        for perm in manager_group.permissions.all():
            self.stdout.write(f'- {perm.codename}') 