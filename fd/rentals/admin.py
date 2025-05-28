from django.contrib import admin
from django.conf import settings
from .models import Transport, RentalApplication
from .forms import RentalApplicationForm
from django.http import HttpResponse, JsonResponse
from docx import Document
from django.template.defaultfilters import date as _date
from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied
import io
import os
from datetime import datetime

# Отменяем регистрацию стандартного UserAdmin
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_groups')
    list_filter = ('is_staff', 'is_superuser', 'groups')
    
    def get_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])
    get_groups.short_description = "Группы"

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
            
        if request.user.is_superuser:
            return (
                (None, {'fields': ('username', 'password')}),
                ('Персональная информация', {'fields': ('first_name', 'last_name', 'email')}),
                ('Права доступа', {
                    'fields': ('is_active', 'is_staff', 'is_superuser', 'groups'),
                }),
            )
        return (
            (None, {'fields': ('username', 'password')}),
            ('Персональная информация', {'fields': ('first_name', 'last_name', 'email')}),
            ('Права доступа', {
                'fields': ('is_active', 'groups'),
            }),
        )

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return ('is_staff', 'is_superuser', 'user_permissions')
        return super().get_readonly_fields(request, obj)

# Отменяем регистрацию стандартного GroupAdmin, так как он нам не нужен
admin.site.unregister(Group)

template_path = os.path.join(settings.BASE_DIR, 'rentals', 'templates', 'contracts', 'rental_contract_template.docx')
doc = Document(template_path)

def create_manager_group():
    """Создает группу менеджеров с необходимыми правами если она не существует"""
    group, created = Group.objects.get_or_create(name='Manager')
    if created:
        # Права для Transport
        transport_permissions = Permission.objects.filter(
            content_type__app_label='rentals',
            content_type__model='transport',
            codename__in=['view_transport']
        )
        # Права для RentalApplication
        rental_permissions = Permission.objects.filter(
            content_type__app_label='rentals',
            content_type__model='rentalapplication',
            codename__in=['add_rentalapplication', 'change_rentalapplication', 'view_rentalapplication']
        )
        
        # Добавляем все разрешения в группу
        group.permissions.set(list(transport_permissions) + list(rental_permissions))

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

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(RentalApplication)
class RentalApplicationAdmin(admin.ModelAdmin):
    form = RentalApplicationForm
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
            'fields': ('rental_start_date', 'rental_end_date', 'transport', 'security_deposit')
        }),
        ('Паспортные данные', {
            'fields': ('passport_number', 'passport_issued_by', 'passport_issue_date')
        }),
    )

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ('created_at', 'updated_at')
        return ()

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

    def generate_contract(self, request, queryset):
        # Проверяем права на генерацию договора
        if not (request.user.is_superuser or request.user.groups.filter(name='Manager').exists()):
            raise PermissionDenied("У вас нет прав на генерацию договора")

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
            'today_date': datetime.now().strftime("%d.%m.%Y"),
        }

        # Проходим по всем параграфам
        for paragraph in doc.paragraphs:
            # Получаем текст всего параграфа
            text = paragraph.text
            # Проверяем, есть ли в параграфе плейсхолдеры
            for key, value in context.items():
                placeholder = f"{{{{ {key} }}}}"
                if placeholder in text:
                    # Заменяем плейсхолдер на значение
                    text = text.replace(placeholder, str(value))
            
            # Если были замены, обновляем текст параграфа
            if text != paragraph.text:
                # Очищаем параграф
                for run in paragraph.runs:
                    run.text = ""
                # Добавляем новый текст с сохранением форматирования первого run
                if paragraph.runs:
                    paragraph.runs[0].text = text
                else:
                    paragraph.add_run(text)

        # Обработка таблиц
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        text = paragraph.text
                        for key, value in context.items():
                            placeholder = f"{{{{ {key} }}}}"
                            if placeholder in text:
                                text = text.replace(placeholder, str(value))
                        
                        if text != paragraph.text:
                            # Очищаем параграф
                            for run in paragraph.runs:
                                run.text = ""
                            # Добавляем новый текст с сохранением форматирования первого run
                            if paragraph.runs:
                                paragraph.runs[0].text = text
                            else:
                                paragraph.add_run(text)

        # Сохранение во временный файл и отдача пользователю
        f = io.BytesIO()
        doc.save(f)
        f.seek(0)
        
        # Формируем имя файла
        filename = f"Договор аренды - {application.full_name} от {datetime.now().strftime('%d.%m.%Y')}.docx"
        # Кодируем имя файла для корректного отображения русских букв
        encoded_filename = filename.encode('utf-8').decode('latin-1')
        
        response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"'
        return response

    generate_contract.short_description = "Печать договора аренды"

    class Media:
        css = {
            'all': (
                'admin/css/forms.css',
                'admin/css/widgets.css',
            )
        }
        js = (
            'admin/js/jquery.init.js',
            'admin/js/core.js',
            'admin/js/calendar.js',
            'admin/js/admin/DateTimeShortcuts.js',
            'rentals/js/rental_form.js',
        )