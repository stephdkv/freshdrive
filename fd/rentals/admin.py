from django.contrib import admin
from django.conf import settings
from .models import Transport, RentalApplication, Client, Calendar
from .forms import RentalApplicationForm
from django.http import HttpResponse, JsonResponse
from docx import Document
from django.template.defaultfilters import date as _date
from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
import io
import os
from datetime import datetime
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render

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
# admin.site.unregister(Group)

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
    list_display = ('number', 'name', 'model', 'year', 'color', 'registration_number', 'vin_number',
                   'price_per_day', 'price_3_6_days', 'price_7_30_days', 'price_30_plus_days')
    search_fields = ('number', 'name', 'model', 'registration_number', 'color', 'vin_number')
    list_filter = ('year',)
    ordering = ('number',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('number', 'name', 'model', 'year', 'color', 'registration_number', 'vin_number')
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
    list_display = ('get_colored_status', 'full_name', 'phone_number', 'transport', 'rental_start_date', 
                   'rental_end_date', 'get_rental_days_display', 'get_rate_type_display',
                   'get_daily_rate_display', 'get_discount_display', 'get_discount_amount_display',
                   'get_security_deposit_display', 'get_total_cost_display')
    list_filter = ('status', 'rental_start_date', 'rental_end_date', 'created_at', 'discount')
    search_fields = ('full_name', 'phone_number', 'passport_number', 
                    'transport__name', 'transport__model')
    date_hierarchy = 'rental_start_date'
    
    fieldsets = (
        ('Информация об арендаторе', {
            'fields': ('full_name', 'phone_number')
        }),
        ('Детали аренды', {
            'fields': ('rental_start_date', 'rental_end_date', 'transport', 'security_deposit', 'discount', 'status')
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

    def get_discount_display(self, obj):
        return f"{obj.discount}%"
    get_discount_display.short_description = 'Скидка'

    def get_discount_amount_display(self, obj):
        return f"{obj.get_discount_amount():,} ₽"
    get_discount_amount_display.short_description = 'Сумма скидки'

    def get_total_cost_display(self, obj):
        return f"{obj.calculate_total_cost():,} ₽"
    get_total_cost_display.short_description = 'Итого со скидкой'

    def get_security_deposit_display(self, obj):
        return f"{int(obj.security_deposit):,} ₽"
    get_security_deposit_display.short_description = 'Обеспечительный платеж'
    
    def make_active(self, request, queryset):
        for application in queryset:
            application.change_status(RentalApplication.STATUS_ACTIVE)
    make_active.short_description = "Сделать активными"

    def make_completed(self, request, queryset):
        for application in queryset:
            application.change_status(RentalApplication.STATUS_COMPLETED)
    make_completed.short_description = "Отметить как завершенные"

    def make_cancelled(self, request, queryset):
        for application in queryset:
            application.change_status(RentalApplication.STATUS_CANCELLED)
    make_cancelled.short_description = "Отметить как отмененные"

    actions = ['generate_contract', 'make_active', 'make_completed', 'make_cancelled']

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
            'transport_model': f"№{transport.number} - {transport.name} {transport.model}",
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

    def get_colored_status(self, obj):
        status_classes = {
            'reserved': 'status-reserved',
            'active': 'status-active',
            'completed': 'status-completed',
            'cancelled': 'status-cancelled',
        }
        return format_html(
            '<span class="status-badge {}">{}</span>',
            status_classes[obj.status],
            obj.get_status_display()
        )
    get_colored_status.short_description = 'Статус'
    get_colored_status.admin_order_field = 'status'

    def changelist_view(self, request, extra_context=None):
        # Get the filtered queryset
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            # Get the filtered queryset
            qs = response.context_data['cl'].queryset
            
            # Calculate totals
            total_cost = sum(app.calculate_total_cost() for app in qs)
            total_security_deposit = sum(int(app.security_deposit or 0) for app in qs)
            total_days = sum(app.get_rental_days() for app in qs)
            
            # Add totals to the context
            response.context_data['total_cost'] = f"{total_cost:,} ₽"
            response.context_data['total_security_deposit'] = f"{total_security_deposit:,} ₽"
            response.context_data['total_days'] = f"{total_days} дн."
            
        except (AttributeError, KeyError):
            # If there's an error, just return the response without totals
            return response
            
        return response

    class Media:
        css = {
            'all': (
                'admin/css/forms.css',
                'admin/css/widgets.css',
                'rentals/css/admin.css',
            )
        }
        js = (
            'admin/js/jquery.init.js',
            'admin/js/core.js',
            'admin/js/calendar.js',
            'admin/js/admin/DateTimeShortcuts.js',
            'rentals/js/rental_form.js',
        )

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'get_rental_count', 'get_last_rental_date', 'created_at')
    search_fields = ('full_name', 'phone_number')
    ordering = ('phone_number',)
    
    def get_rental_count(self, obj):
        return obj.rental_applications.count()
    get_rental_count.short_description = 'Количество заявок'
    
    def get_last_rental_date(self, obj):
        last_rental = obj.rental_applications.order_by('-rental_start_date').first()
        if last_rental:
            return last_rental.rental_start_date
        return '-'
    get_last_rental_date.short_description = 'Последняя аренда'

    fieldsets = (
        ('Основная информация', {
            'fields': ('full_name', 'phone_number')
        }),
        ('История заявок', {
            'fields': ('get_rental_history',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('get_rental_history',)

    def get_rental_history(self, obj):
        rentals = obj.rental_applications.all().order_by('-rental_start_date')
        if not rentals:
            return "Нет заявок"
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '''
            <tr style="background-color: #f8f9fa;">
                <th style="padding: 8px; border: 1px solid #ddd;">Статус</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Транспорт</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Период</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Сумма</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Действия</th>
            </tr>
        '''
        
        for rental in rentals:
            status_class = {
                'reserved': 'status-reserved',
                'active': 'status-active',
                'completed': 'status-completed',
                'cancelled': 'status-cancelled',
            }.get(rental.status, '')
            
            html += f'''
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <span class="status-badge {status_class}">{rental.get_status_display()}</span>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{rental.transport}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        {rental.rental_start_date.strftime('%d.%m.%Y')} - {rental.rental_end_date.strftime('%d.%m.%Y')}
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{rental.calculate_total_cost():,} ₽</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <a href="/admin/rentals/rentalapplication/{rental.id}/change/" class="button" style="padding: 5px 10px; background: #417690; color: white; text-decoration: none; border-radius: 4px;">Просмотр</a>
                    </td>
                </tr>
            '''
        
        html += '</table>'
        return format_html(html)
    get_rental_history.short_description = 'История заявок'

    class Media:
        css = {
            'all': (
                'admin/css/forms.css',
                'admin/css/widgets.css',
                'rentals/css/admin.css',
            )
        }

@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ('transport', 'title', 'start', 'end', 'status')
    list_filter = ('transport', 'status')
    search_fields = ('title', 'transport__name', 'transport__model')
    date_hierarchy = 'start'

    @staticmethod
    def calendar_view(request):
        transports = Transport.objects.all()
        context = {
            'transports': transports,
            'title': 'Календарь аренды',
            'opts': Calendar._meta,
        }
        return render(request, 'admin/calendar.html', context)

    @staticmethod
    def calendar_events(request):
        try:
            transport_id = request.GET.get('transport_id')
            start = request.GET.get('start')
            end = request.GET.get('end')

            if not transport_id:
                return JsonResponse({'error': 'Transport ID is required'}, status=400)

            events = Calendar.objects.filter(transport_id=transport_id)
            
            if start:
                try:
                    # FullCalendar отправляет даты в формате YYYY-MM-DD
                    start_date = datetime.strptime(start.split('T')[0], '%Y-%m-%d')
                    events = events.filter(start__date__gte=start_date.date())
                except (ValueError, IndexError) as e:
                    return JsonResponse({'error': f'Invalid start date format: {str(e)}'}, status=400)
            
            if end:
                try:
                    # FullCalendar отправляет даты в формате YYYY-MM-DD
                    end_date = datetime.strptime(end.split('T')[0], '%Y-%m-%d')
                    events = events.filter(end__date__lte=end_date.date())
                except (ValueError, IndexError) as e:
                    return JsonResponse({'error': f'Invalid end date format: {str(e)}'}, status=400)

            events_data = []
            for event in events:
                color = {
                    RentalApplication.STATUS_RESERVED: '#ffc107',  # желтый
                    RentalApplication.STATUS_ACTIVE: '#28a745',    # зеленый
                    RentalApplication.STATUS_COMPLETED: '#17a2b8', # голубой
                    RentalApplication.STATUS_CANCELLED: '#dc3545', # красный
                }.get(event.status, '#6c757d')  # серый по умолчанию

                events_data.append({
                    'id': event.rental_application.id if event.rental_application else event.id,
                    'title': event.title,
                    'start': event.start.isoformat(),
                    'end': event.end.isoformat(),
                    'allDay': event.all_day,
                    'color': color,
                    'url': f'/admin/rentals/rentalapplication/{event.rental_application.id}/change/' if event.rental_application else None,
                })

            return JsonResponse(events_data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_calendar_link'] = True
        return super().changelist_view(request, extra_context=extra_context)

    class Media:
        css = {
            'all': ('admin/css/forms.css',)
        }
        js = ('admin/js/calendar.js',)