from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth.models import User
from django.conf import settings

# Варианты для поля "Откуда о нас узнали"
HOW_DID_YOU_FIND_US_CHOICES = [
    ("friends", "От друзей / знакомых"),
    ("internet", "Из интернета / через поиск (Google, Яндекс)"),
    ("ads", "Увидел рекламу"),
    ("repeat_customer", "У вас брал услугу раньше / уже был клиентом"),
    ("catalog", "Нашли вас в каталоге / на картах (Google Maps, 2ГИС, Яндекс.Справочник)"),
    ("other", "Другое"),
]

CITY_CHOICES = [
    ('sochi', 'Сочи'),
    ('adler', 'Адлер'),
]

class Client(models.Model):
    full_name = models.CharField('ФИО', max_length=200)
    phone_number = PhoneNumberField('Телефон', unique=True)
    passport_number = models.CharField('Номер паспорта', max_length=50, help_text="Номер паспорта", null=True, blank=True)
    passport_issued_by = models.CharField('Кем выдан', max_length=200, help_text="Орган, выдавший паспорт", null=True, blank=True)
    passport_issue_date = models.DateField('Дата выдачи', help_text="Дата выдачи паспорта", null=True, blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    how_did_you_find_us = models.CharField(
        "Откуда о нас узнали",
        max_length=32,
        choices=HOW_DID_YOU_FIND_US_CHOICES,
        null=True,
        blank=True,
        help_text="Как клиент узнал о нас"
    )
    city = models.CharField('Город', max_length=16, choices=CITY_CHOICES, default='sochi')

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['phone_number']

class Transport(models.Model):
    number = models.PositiveIntegerField('Номер', help_text="Порядковый номер транспорта", null=True, blank=True)
    name = models.CharField('Название', max_length=200)
    model = models.CharField('Модель', max_length=200)
    year = models.IntegerField('Год выпуска')
    color = models.CharField('Цвет', max_length=50, null=True, blank=True)
    registration_number = models.CharField('Регистрационный номер', max_length=50,  null=True, blank=True)
    vin_number = models.CharField('VIN номер', max_length=17, help_text="17-значный идентификационный номер транспортного средства", default=0, null=True)
    price_per_day = models.DecimalField('Цена за сутки', max_digits=10, decimal_places=2, default=0)
    price_3_6_days = models.DecimalField('Цена за 3-6 суток (за сутки)', max_digits=10, decimal_places=2, default=0)
    price_7_30_days = models.DecimalField('Цена за 7-30 суток (за сутки)', max_digits=10, decimal_places=2, default=0)
    price_30_plus_days = models.DecimalField('Цена от 30 суток (за сутки)', max_digits=10, decimal_places=2, default=0)
    city = models.CharField('Город', max_length=16, choices=CITY_CHOICES, default='sochi')
    
    def check_availability(self, start_date, end_date, exclude_booking_id=None):
        """
        Проверяет, доступен ли транспорт в указанный период
        
        Args:
            start_date: дата начала аренды
            end_date: дата окончания аренды
            exclude_booking_id: ID брони для исключения (при редактировании)
            
        Returns:
            tuple: (bool, str) - (доступен ли, сообщение о причине недоступности)
        """
        # Проверяем пересечение с существующими бронями
        overlapping_bookings = self.rental_applications.filter(
            Q(rental_start_date__lte=end_date) & 
            Q(rental_end_date__gte=start_date) &
            ~Q(status__in=[RentalApplication.STATUS_CANCELLED, RentalApplication.STATUS_COMPLETED])  # Исключаем отмененные и завершенные заявки
        )
        
        # Исключаем текущую бронь при редактировании
        if exclude_booking_id:
            overlapping_bookings = overlapping_bookings.exclude(id=exclude_booking_id)
        
        if overlapping_bookings.exists():
            booking = overlapping_bookings.first()
            return False, f"Транспорт забронирован с {booking.rental_start_date.strftime('%d.%m.%Y')} по {booking.rental_end_date.strftime('%d.%m.%Y')}"
            
        return True, "Транспорт доступен в указанные даты"
    
    def __str__(self):
        return f"№{self.number} - {self.name} {self.model}"
    
    class Meta:
        verbose_name = "Транспорт"
        verbose_name_plural = "Транспорт"

class RentalApplication(models.Model):
    # Статусы заявки
    STATUS_RESERVED = 'reserved'
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_OVERDUE = 'overdue'
    
    STATUS_CHOICES = [
        (STATUS_RESERVED, 'Резерв'),
        (STATUS_ACTIVE, 'Активная'),
        (STATUS_COMPLETED, 'Завершенная'),
        (STATUS_CANCELLED, 'Отмененная'),
        (STATUS_OVERDUE, 'Просрочена'),
    ]

    DISCOUNT_CHOICES = [
        (0, 'Без скидки'),
        (10, '10%'),
        (20, '20%'),
    ]

    client = models.ForeignKey(Client, verbose_name='Клиент', on_delete=models.PROTECT, related_name='rental_applications', null=True, blank=True)
    full_name = models.CharField('ФИО', max_length=200, help_text="Полное имя арендатора")
    phone_number = PhoneNumberField('Телефон', help_text="Контактный номер телефона.")
    rental_start_date = models.DateField('Дата начала аренды', help_text="Дата начала аренды")
    rental_end_date = models.DateField('Дата окончания аренды', help_text="Дата окончания аренды")
    passport_number = models.CharField('Номер паспорта', max_length=50, help_text="Номер паспорта", null=True, blank=True)
    passport_issued_by = models.CharField('Кем выдан', max_length=200, help_text="Орган, выдавший паспорт", null=True, blank=True)
    passport_issue_date = models.DateField('Дата выдачи', help_text="Дата выдачи паспорта", null=True, blank=True)
    transport = models.ForeignKey(Transport, verbose_name='Транспорт', on_delete=models.PROTECT, related_name='rental_applications')
    security_deposit = models.DecimalField('Залог', max_digits=10, decimal_places=0, default=0,
                                         help_text="Сумма Залога", null=True, blank=True)
    discount = models.IntegerField('Скидка', choices=DISCOUNT_CHOICES, default=0, help_text="Скидка на аренду")
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RESERVED,
        help_text="Текущий статус заявки"
    )
    how_did_you_find_us = models.CharField(
        "Откуда о нас узнали",
        max_length=32,
        choices=HOW_DID_YOU_FIND_US_CHOICES,
        null=True,
        blank=True,
        help_text="Как клиент узнал о нас"
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    original_total_cost = models.DecimalField('Исходная сумма аренды', max_digits=10, decimal_places=0, null=True, blank=True, help_text='Сумма аренды до досрочного возврата (для внутреннего пользования)')
    city = models.CharField('Город', max_length=16, choices=CITY_CHOICES, default='sochi')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Менеджер',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_rental_applications'
    )
    activated_at = models.DateTimeField(null=True, blank=True, verbose_name="Время активации")
  
    def clean(self):
        """Валидация заявки на аренду"""
        if self.rental_start_date and self.rental_end_date:
            # Проверка корректности дат
            if self.rental_start_date > self.rental_end_date:
                raise ValidationError({
                    'rental_end_date': 'Дата окончания аренды не может быть раньше даты начала'
                })
            
            # if self.rental_start_date < datetime.now().date():
            #     raise ValidationError({
            #         'rental_start_date': 'Дата начала аренды не может быть в прошлом'
            #     })
            
            # Проверка доступности транспорта только если он выбран
            if hasattr(self, 'transport_id') and self.transport_id:
                is_available, message = self.transport.check_availability(
                    self.rental_start_date,
                    self.rental_end_date,
                    exclude_booking_id=self.id
                )
                if not is_available:
                    raise ValidationError({
                        'transport': message
                    })
    
    def save(self, *args, **kwargs):
        # Создаем или находим клиента при сохранении заявки
        if not self.client:
            client, created = Client.objects.get_or_create(
                phone_number=self.phone_number,
                defaults={'full_name': self.full_name}
            )
            self.client = client
        
        # Обновляем данные клиента, если они изменились
        if self.client:
            updated = False
            
            # Обновляем имя, если оно изменилось
            if self.client.full_name != self.full_name:
                self.client.full_name = self.full_name
                updated = True
            
            # Обновляем паспортные данные, если они есть в заявке
            if self.passport_number and self.client.passport_number != self.passport_number:
                self.client.passport_number = self.passport_number
                updated = True
            
            if self.passport_issued_by and self.client.passport_issued_by != self.passport_issued_by:
                self.client.passport_issued_by = self.passport_issued_by
                updated = True
            
            if self.passport_issue_date and self.client.passport_issue_date != self.passport_issue_date:
                self.client.passport_issue_date = self.passport_issue_date
                updated = True
            
            # Обновляем поле how_did_you_find_us, если оно есть в заявке и отличается
            if self.how_did_you_find_us and self.client.how_did_you_find_us != self.how_did_you_find_us:
                self.client.how_did_you_find_us = self.how_did_you_find_us
                updated = True
            
            # Сохраняем клиента, если были изменения
            if updated:
                self.client.save()
        
        self.clean()
        
        # Сохраняем исходную сумму аренды при первом переводе в статус Активная
        if self.status == self.STATUS_ACTIVE and not self.original_total_cost:
            self.original_total_cost = self.calculate_total_cost()
        
        # Создаем или обновляем событие в календаре
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Создаем или обновляем событие в календаре
        calendar_event, created = Calendar.objects.get_or_create(
            rental_application=self,
            defaults={
                'transport': self.transport,
                'title': f"Аренда: {self.full_name}",
                'start': datetime.combine(self.rental_start_date, datetime.min.time()),
                'end': datetime.combine(self.rental_end_date, datetime.max.time()),
                'status': self.status,
                'city': self.city
            }
        )
        
        if not created:
            calendar_event.transport = self.transport
            calendar_event.title = f"Аренда: {self.full_name}"
            calendar_event.start = datetime.combine(self.rental_start_date, datetime.min.time())
            calendar_event.end = datetime.combine(self.rental_end_date, datetime.max.time())
            calendar_event.status = self.status
            calendar_event.city = self.city
            calendar_event.save()

    def delete(self, *args, **kwargs):
        # Удаляем связанное событие календаря при удалении заявки
        Calendar.objects.filter(rental_application=self).delete()
        super().delete(*args, **kwargs)
    
    def get_rental_days(self):
        """Вычисляет количество дней аренды"""
        if not self.rental_start_date or not self.rental_end_date:
            return 0
        delta = self.rental_end_date - self.rental_start_date
        return delta.days  # Убираем +1, так как нам нужны только полные сутки
    
    def get_daily_rate(self):
        """Определяет тариф за сутки в зависимости от длительности аренды"""
        days = self.get_rental_days()
        if not self.transport or days <= 0:
            return 0
        if days <= 2:
            return int(self.transport.price_per_day)
        elif 3 <= days <= 6:
            return int(self.transport.price_3_6_days)
        elif 7 <= days <= 29:
            return int(self.transport.price_7_30_days)
        else:  # 30 и более дней
            return int(self.transport.price_30_plus_days)
    
    def calculate_total_cost(self):
        """Вычисляет общую стоимость аренды с учетом скидки"""
        daily_rate = self.get_daily_rate()
        days = self.get_rental_days()
        if daily_rate == 0 or days == 0:
            return 0
        base_cost = int(daily_rate * days)
        discount_amount = base_cost * (self.discount / 100)
        return int(base_cost - discount_amount)
    
    def get_discount_amount(self):
        """Возвращает сумму скидки"""
        daily_rate = self.get_daily_rate()
        days = self.get_rental_days()
        if daily_rate == 0 or days == 0:
            return 0
        base_cost = int(daily_rate * days)
        return int(base_cost * (self.discount / 100))
    
    def get_rate_type(self):
        """Возвращает тип примененного тарифа"""
        days = self.get_rental_days()
        if days <= 2:
            return "Базовый тариф"
        elif 3 <= days <= 6:
            return "Тариф 3-6 дней"
        elif 7 <= days <= 29:
            return "Тариф 7-30 дней"
        else:
            return "Тариф от 30 дней"
    
    def get_status_display_class(self):
        """Возвращает CSS класс для отображения статуса"""
        status_classes = {
            self.STATUS_RESERVED: 'status-reserved',
            self.STATUS_ACTIVE: 'status-active',
            self.STATUS_COMPLETED: 'status-completed',
            self.STATUS_CANCELLED: 'status-cancelled',
        }
        return status_classes.get(self.status, '')

    def can_change_status_to(self, new_status):
        """Проверяет, можно ли изменить статус на указанный"""
        # Словарь допустимых переходов статуса
        allowed_transitions = {
            self.STATUS_RESERVED: [self.STATUS_ACTIVE, self.STATUS_CANCELLED],
            self.STATUS_ACTIVE: [self.STATUS_COMPLETED, self.STATUS_CANCELLED],
            self.STATUS_COMPLETED: [],  # Завершенную заявку нельзя изменить
            self.STATUS_CANCELLED: [],  # Отмененную заявку нельзя изменить
        }
        return new_status in allowed_transitions.get(self.status, [])

    def change_status(self, new_status):
        """Изменяет статус заявки если это допустимо"""
        if self.can_change_status_to(new_status):
            self.status = new_status
            self.save()
            return True
        return False

    def __str__(self):
        return f"Аренда от {self.full_name} ({self.rental_start_date} до {self.rental_end_date}) - {self.get_status_display()}"
    
    class Meta:
        verbose_name = "Заявка на аренду"
        verbose_name_plural = "Заявки на аренду"
        ordering = ['-created_at'] 

    def complete_early(self, new_end_date=None):
        """Досрочно завершить аренду, пересчитать сумму и сменить статус на Завершенная. new_end_date — дата возврата (по умолчанию сегодня)."""
        if self.status != self.STATUS_ACTIVE:
            raise ValueError('Досрочно завершить можно только активную аренду!')
        if not new_end_date:
            from datetime import date
            new_end_date = date.today()
        if new_end_date < self.rental_start_date:
            raise ValueError('Дата возврата не может быть раньше даты начала аренды!')
        self.rental_end_date = new_end_date
        self.status = self.STATUS_COMPLETED
        self.save()
        return True

    @property
    def is_overdue(self):
        from django.utils import timezone
        import pytz
        from datetime import timedelta
        if self.status == self.STATUS_ACTIVE and self.rental_end_date:
            tz = pytz.timezone('Europe/Moscow')
            # Просроченной считается с 00:00 следующего дня после rental_end_date
            overdue_dt = datetime.combine(self.rental_end_date, datetime.min.time()) + timedelta(days=1)
            overdue_dt = tz.localize(overdue_dt)
            now = timezone.localtime(timezone.now(), tz)
            return now >= overdue_dt
        return False

class Calendar(models.Model):
    transport = models.ForeignKey(Transport, verbose_name='Транспорт', on_delete=models.CASCADE, related_name='calendar_events')
    title = models.CharField('Название события', max_length=200)
    start = models.DateTimeField('Начало')
    end = models.DateTimeField('Конец')
    all_day = models.BooleanField('Весь день', default=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=RentalApplication.STATUS_CHOICES,
        default=RentalApplication.STATUS_RESERVED
    )
    rental_application = models.ForeignKey(
        RentalApplication,
        verbose_name='Заявка на аренду',
        on_delete=models.CASCADE,
        related_name='calendar_events',
        null=True,
        blank=True
    )
    city = models.CharField('Город', max_length=16, choices=CITY_CHOICES, default='sochi')

    def __str__(self):
        return f"{self.transport} - {self.title} ({self.start.date()} - {self.end.date()})"

    class Meta:
        verbose_name = "Событие календаря"
        verbose_name_plural = "События календаря"
        ordering = ['start'] 

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    city = models.CharField('Город', max_length=16, choices=CITY_CHOICES, default='sochi')

    def __str__(self):
        return f"{self.user.username} ({self.get_city_display()})"

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей' 