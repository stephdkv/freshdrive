from django.contrib.auth.models import User
from rentals.models import RentalApplication, UserProfile

print('ПРОФИЛИ ПОЛЬЗОВАТЕЛЕЙ:')
for user in User.objects.all():
    try:
        city = user.profile.city
    except Exception:
        city = '---'
    print(f'User: {user.username:20} | Город профиля: {city}')

print('\nЗАЯВКИ:')
for app in RentalApplication.objects.all():
    print(f'Заявка id={app.id:4} | ФИО: {app.full_name:25} | Город заявки: {app.city}') 