from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db.models import Q

class Transport(models.Model):
    name = models.CharField('Название', max_length=200)
    model = models.CharField('Модель', max_length=200)
    year = models.IntegerField('Год выпуска')
    color = models.CharField('Цвет', max_length=50, null=True, blank=True)
    registration_number = models.CharField('Регистрационный номер', max_length=50)
    vin_number = models.CharField('VIN номер', max_length=17, help_text="17-значный идентификационный номер транспортного средства", default=0, null=True)
    price_per_day = models.DecimalField('Цена за сутки', max_digits=10, decimal_places=2, default=0)
    price_3_6_days = models.DecimalField('Цена за 3-6 суток (за сутки)', max_digits=10, decimal_places=2, default=0)
    price_7_30_days = models.DecimalField('Цена за 7-30 суток (за сутки)', max_digits=10, decimal_places=2, default=0)
    price_30_plus_days = models.DecimalField('Цена от 30 суток (за сутки)', max_digits=10, decimal_places=2, default=0)
    
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
            Q(rental_end_date__gte=start_date)
        )
        
        # Исключаем текущую бронь при редактировании
        if exclude_booking_id:
            overlapping_bookings = overlapping_bookings.exclude(id=exclude_booking_id)
        
        if overlapping_bookings.exists():
            booking = overlapping_bookings.first()
            return False, f"Транспорт забронирован с {booking.rental_start_date.strftime('%d.%m.%Y')} по {booking.rental_end_date.strftime('%d.%m.%Y')}"
            
        return True, "Транспорт доступен в указанные даты"
    
    def __str__(self):
        return f"{self.name} {self.model} ({self.vin_number})"
    
    class Meta:
        verbose_name = "Транспорт"
        verbose_name_plural = "Транспорт"

class RentalApplication(models.Model):
    full_name = models.CharField('ФИО', max_length=200, help_text="Полное имя арендатора")
    phone_number = PhoneNumberField('Телефон', help_text="Контактный номер телефона")
    rental_start_date = models.DateField('Дата начала аренды', help_text="Дата начала аренды")
    rental_end_date = models.DateField('Дата окончания аренды', help_text="Дата окончания аренды")
    passport_number = models.CharField('Номер паспорта', max_length=50, help_text="Номер паспорта")
    passport_issued_by = models.CharField('Кем выдан', max_length=200, help_text="Орган, выдавший паспорт")
    passport_issue_date = models.DateField('Дата выдачи', help_text="Дата выдачи паспорта")
    transport = models.ForeignKey(Transport, verbose_name='Транспорт', on_delete=models.PROTECT, related_name='rental_applications')
    security_deposit = models.DecimalField('Обеспечительный платеж', max_digits=10, decimal_places=0, default=0,
                                         help_text="Сумма обеспечительного платежа")
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    def clean(self):
        """Валидация заявки на аренду"""
        if self.rental_start_date and self.rental_end_date:
            # Проверка корректности дат
            if self.rental_start_date > self.rental_end_date:
                raise ValidationError({
                    'rental_end_date': 'Дата окончания аренды не может быть раньше даты начала'
                })
            
            if self.rental_start_date < datetime.now().date():
                raise ValidationError({
                    'rental_start_date': 'Дата начала аренды не может быть в прошлом'
                })
            
            # Проверка доступности транспорта
            if self.transport:
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
        self.clean()
        super().save(*args, **kwargs)
    
    def get_rental_days(self):
        """Вычисляет количество дней аренды"""
        delta = self.rental_end_date - self.rental_start_date
        return delta.days + 1  # +1 так как включаем обе даты
    
    def get_daily_rate(self):
        """Определяет тариф за сутки в зависимости от длительности аренды"""
        days = self.get_rental_days()
        
        if days <= 2:
            return int(self.transport.price_per_day)
        elif 3 <= days <= 6:
            return int(self.transport.price_3_6_days)
        elif 7 <= days <= 29:
            return int(self.transport.price_7_30_days)
        else:  # 30 и более дней
            return int(self.transport.price_30_plus_days)
    
    def calculate_total_cost(self):
        """Вычисляет общую стоимость аренды"""
        return int(self.get_daily_rate() * self.get_rental_days())
    
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
    
    def __str__(self):
        return f"Аренда от {self.full_name} ({self.rental_start_date} до {self.rental_end_date})"
    
    class Meta:
        verbose_name = "Заявка на аренду"
        verbose_name_plural = "Заявки на аренду"
        ordering = ['-created_at'] 