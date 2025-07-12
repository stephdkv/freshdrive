from django.core.management.base import BaseCommand
from rentals.models import RentalApplication
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Заполняет поле created_by для заявок, у которых оно пустое'

    def handle(self, *args, **options):
        # Получаем заявки без created_by
        applications_without_creator = RentalApplication.objects.filter(created_by__isnull=True)
        count = applications_without_creator.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('Все заявки уже имеют заполненное поле created_by'))
            return
            
        self.stdout.write(f'Найдено {count} заявок без created_by')
        
        # Получаем первого суперпользователя как создателя по умолчанию
        try:
            default_creator = User.objects.filter(is_superuser=True).first()
            if not default_creator:
                self.stdout.write(self.style.ERROR('Не найден суперпользователь для заполнения created_by'))
                return
                
            # Обновляем заявки
            updated = applications_without_creator.update(created_by=default_creator)
            
            self.stdout.write(
                self.style.SUCCESS(f'Успешно обновлено {updated} заявок. Создатель: {default_creator.username}')
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при обновлении: {e}')) 