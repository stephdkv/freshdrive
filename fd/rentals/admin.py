from django.contrib import admin
from django.conf import settings
from .models import Transport, RentalApplication
from django.http import HttpResponse
from docx import Document
from django.template.defaultfilters import date as _date
import io
import os
from datetime import datetime

template_path = os.path.join(settings.BASE_DIR, 'rentals', 'templates', 'contracts', 'rental_contract_template.docx')
doc = Document(template_path)

@admin.register(Transport)
class TransportAdmin(admin.ModelAdmin):
    list_display = ('name', 'model', 'year', 'color', 'registration_number', 'vin_number',
                   'price_per_day', 'price_3_6_days', 'price_7_30_days', 'price_30_plus_days')
    search_fields = ('name', 'model', 'registration_number', 'color', 'vin_number')
    list_filter = ('year',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'model', 'year', 'color', 'registration_number', 'vin_number')
        }),
        ('Цены', {
            'fields': ('price_per_day', 'price_3_6_days', 'price_7_30_days', 'price_30_plus_days')
        }),
    )

@admin.register(RentalApplication)
class RentalApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'transport', 'rental_start_date', 
                   'rental_end_date', 'get_rental_days_display', 'get_rate_type_display',
                   'get_daily_rate_display', 'get_total_cost_display', 'get_security_deposit_display')
    list_filter = ('rental_start_date', 'rental_end_date', 'created_at')
    search_fields = ('full_name', 'phone_number', 'passport_number', 
                    'transport__name', 'transport__model')
    date_hierarchy = 'rental_start_date'
    
    fieldsets = (
        ('Информация об арендаторе', {
            'fields': ('full_name', 'phone_number')
        }),
        ('Детали аренды', {
            'fields': ('rental_start_date', 'rental_end_date', 'transport',  'security_deposit')
        }),
        ('Паспортные данные', {
            'fields': ('passport_number', 'passport_issued_by', 'passport_issue_date')
        }),
    )

    def get_rental_days_display(self, obj):
        return f"{obj.get_rental_days()} дн."
    get_rental_days_display.short_description = 'Срок аренды'

    def get_rate_type_display(self, obj):
        return obj.get_rate_type()
    get_rate_type_display.short_description = 'Тип тарифа'

    def get_daily_rate_display(self, obj):
        return f"{obj.get_daily_rate():,} ₽/день"
    get_daily_rate_display.short_description = 'Тариф'

    def get_total_cost_display(self, obj):
        return f"{obj.calculate_total_cost():,} ₽"
    get_total_cost_display.short_description = 'Итого'

    def get_security_deposit_display(self, obj):
        return f"{int(obj.security_deposit):,} ₽"
    get_security_deposit_display.short_description = 'Обеспечительный платеж'
    
    actions = ['generate_contract']

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ('created_at', 'updated_at')
        return () 

    def generate_contract(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Выберите одну заявку для генерации договора.", level='error')
            return

        application = queryset.first()
        transport = application.transport

        # Загрузка шаблона
        doc = Document(template_path)

        # Замена всех {{ ... }} на реальные значения
        context = {
            'full_name': application.full_name,
            'phone_number': application.phone_number,
            'color': transport.color,
            'passport_number': application.passport_number,
            'passport_issued_by': application.passport_issued_by,
            'passport_issue_date': _date(application.passport_issue_date, "d.m.Y"),
            'rental_start_date': _date(application.rental_start_date, "d.m.Y"),
            'rental_end_date': _date(application.rental_end_date, "d.m.Y"),
            'transport_model': f"{transport.name} {transport.model}",
            'registration_number': transport.registration_number,
            'vin_number': transport.vin_number,
            'rental_days': application.get_rental_days(),
            'rate_type': application.get_rate_type(),
            'daily_rate': application.get_daily_rate(),
            'total_cost': application.calculate_total_cost(),
            'security_deposit': int(application.security_deposit),
        }

        # Проходим по всем параграфам и таблицам, сохраняя форматирование
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                text = run.text
                for key, value in context.items():
                    placeholder = f"{{{{ {key} }}}}"
                    if placeholder in text:
                        # Сохраняем форматирование, заменяя только текст
                        run.text = text.replace(placeholder, str(value))

        # Обработка таблиц
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            text = run.text
                            for key, value in context.items():
                                placeholder = f"{{{{ {key} }}}}"
                                if placeholder in text:
                                    run.text = text.replace(placeholder, str(value))

        # Сохранение во временный файл и отдача пользователю
        f = io.BytesIO()
        doc.save(f)
        f.seek(0)
        response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="Договор аренды - {application.full_name}.docx"'
        return response

    generate_contract.short_description = "Печать договора аренды"