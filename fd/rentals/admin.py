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
from django.db.models import Sum, Q
import io
import os
from datetime import datetime, date, timedelta
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from urllib.parse import quote
from django.contrib.admin.views.decorators import staff_member_required
import json

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
                   'get_security_deposit_display', 'get_total_cost_display', 'how_did_you_find_us')
    list_filter = ('status', 'rental_start_date', 'rental_end_date', 'created_at', 'discount', 'how_did_you_find_us')
    search_fields = ('full_name', 'phone_number', 'passport_number', 
                    'transport__name', 'transport__model')
    date_hierarchy = 'rental_start_date'
    
    fieldsets = (
        ('Информация об арендаторе', {
            'fields': ('client', 'full_name', 'phone_number', 'how_did_you_find_us')
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
        # Менеджер может менять только transport и status
        if obj and request.user.groups.filter(name='Manager').exists() and not request.user.is_superuser:
            editable = {'transport', 'status'}
            all_fields = set(f.name for f in self.model._meta.fields)
            readonly = list(all_fields - editable)
            # created_at и updated_at тоже должны быть readonly
            readonly += ['created_at', 'updated_at']
            return readonly
        # Для суперпользователя только created_at и updated_at readonly при редактировании
        if obj and request.user.is_superuser:
            return ('created_at', 'updated_at')
        return ()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Если это создание новой заявки и есть параметры клиента в URL
        if not obj and request.method == 'GET':
            client_id = request.GET.get('client_id')
            full_name = request.GET.get('full_name')
            phone_number = request.GET.get('phone_number')
            passport_number = request.GET.get('passport_number')
            passport_issued_by = request.GET.get('passport_issued_by')
            passport_issue_date = request.GET.get('passport_issue_date')
            
            if client_id and full_name and phone_number:
                # Предзаполняем поля данными клиента
                form.base_fields['full_name'].initial = full_name
                form.base_fields['phone_number'].initial = phone_number
                
                # Предзаполняем паспортные данные, если они есть
                if passport_number:
                    form.base_fields['passport_number'].initial = passport_number
                if passport_issued_by:
                    form.base_fields['passport_issued_by'].initial = passport_issued_by
                if passport_issue_date:
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(passport_issue_date, '%Y-%m-%d').date()
                        form.base_fields['passport_issue_date'].initial = date_obj
                    except ValueError:
                        pass
                
                # Устанавливаем клиента
                try:
                    from .models import Client
                    client = Client.objects.get(id=client_id)
                    form.base_fields['client'].initial = client
                except Client.DoesNotExist:
                    pass
        
        return form

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

    def complete_early_and_print_addendum(self, request, queryset):
        """Досрочно завершить аренду и распечатать Дополнение к договору (return.docx)"""
        if queryset.count() != 1:
            self.message_user(request, "Выберите одну активную заявку для досрочного завершения.", level='error')
            return
        application = queryset.first()
        if application.status != RentalApplication.STATUS_ACTIVE:
            self.message_user(request, "Досрочно завершить можно только активную аренду!", level='error')
            return
        try:
            application.complete_early()
        except Exception as e:
            self.message_user(request, f"Ошибка: {e}", level='error')
            return
        return self.generate_return_addendum(request, application)
    complete_early_and_print_addendum.short_description = "Досрочно завершить и распечатать Дополнение"

    def generate_return_addendum(self, request, application):
        """Генерирует и возвращает Дополнение к договору (return.docx)"""
        import io
        from docx import Document
        import os
        from django.conf import settings
        from django.http import HttpResponse
        from django.template.defaultfilters import date as _date
        from datetime import datetime
        # Путь к шаблону
        template_path = os.path.join(settings.BASE_DIR, 'rentals', 'templates', 'contracts', 'return.docx')
        doc = Document(template_path)
        transport = application.transport
        # Фактические значения для доп. соглашения
        actual_return_date = application.rental_end_date
        actual_rental_days = application.get_rental_days()
        actual_cost = application.calculate_total_cost()
        # Для возврата: если был внесен депозит, и actual_cost < изначальной суммы, считаем возврат
        # (допустим, изначальная сумма = application.total_cost_before_early, если нужно — добавить в модель)
        # Здесь просто считаем разницу между старой и новой суммой, если нужно
        refund_amount = 0
        if application.original_total_cost:
            refund_amount = max(0, int(application.original_total_cost) - int(actual_cost))
        # Если нет — не выводим
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
            # Новые поля:
            'actual_return_date': _date(actual_return_date, "d.m.Y"),
            'actual_rental_days': actual_rental_days,
            'actual_cost': actual_cost,
            'refund_amount': refund_amount,
        }
        # Замена плейсхолдеров
        for paragraph in doc.paragraphs:
            text = paragraph.text
            for key, value in context.items():
                placeholder = f"{{{{ {key} }}}}"
                if placeholder in text:
                    text = text.replace(placeholder, str(value))
            if text != paragraph.text:
                for run in paragraph.runs:
                    run.text = ""
                if paragraph.runs:
                    paragraph.runs[0].text = text
                else:
                    paragraph.add_run(text)
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
                            for run in paragraph.runs:
                                run.text = ""
                            if paragraph.runs:
                                paragraph.runs[0].text = text
                            else:
                                paragraph.add_run(text)
        f = io.BytesIO()
        doc.save(f)
        f.seek(0)
        filename = f"Дополнение к договору - {application.full_name} от {datetime.now().strftime('%d.%m.%Y')}.docx"
        encoded_filename = filename.encode('utf-8').decode('latin-1')
        response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename=\"{encoded_filename}\"'
        return response

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
        template_path = os.path.join(settings.BASE_DIR, 'rentals', 'templates', 'contracts', 'rental_contract_template.docx')
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
            text = paragraph.text
            for key, value in context.items():
                placeholder = f"{{{{ {key} }}}}"
                if placeholder in text:
                    text = text.replace(placeholder, str(value))
            if text != paragraph.text:
                for run in paragraph.runs:
                    run.text = ""
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
                            for run in paragraph.runs:
                                run.text = ""
                            if paragraph.runs:
                                paragraph.runs[0].text = text
                            else:
                                paragraph.add_run(text)

        # Сохранение во временный файл и отдача пользователю
        f = io.BytesIO()
        doc.save(f)
        f.seek(0)
        filename = f"Договор аренды - {application.full_name} от {datetime.now().strftime('%d.%m.%Y')}.docx"
        encoded_filename = filename.encode('utf-8').decode('latin-1')
        response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"'
        return response
    generate_contract.short_description = "Печать договора аренды"

    actions = ['generate_contract', 'make_active', 'make_completed', 'make_cancelled', 'complete_early_and_print_addendum']

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

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('analytics/', self.admin_site.admin_view(self.analytics_view), name='rentalapplication_analytics'),
        ]
        return custom_urls + urls

    def analytics_view(self, request):
        from django.db.models import Count, Sum
        from .models import RentalApplication
        import datetime
        # Пример простой аналитики
        total = RentalApplication.objects.count()
        by_status = list(RentalApplication.objects.values('status').annotate(count=Count('id')).order_by('status'))
        total_sum = RentalApplication.objects.aggregate(total=Sum('security_deposit'))['total']
        # Топ-10 клиентов по количеству заявок
        from .models import Client
        top_clients = Client.objects.annotate(num=Count('rental_applications')).order_by('-num')[:10]
        # Динамика по месяцам
        months = []
        now = datetime.date.today()
        for i in range(11, -1, -1):
            month = (now.replace(day=1) - datetime.timedelta(days=30*i)).replace(day=1)
            months.append(month)
        month_labels = [m.strftime('%Y-%m') for m in months]
        month_counts = [RentalApplication.objects.filter(created_at__year=m.year, created_at__month=m.month).count() for m in months]
        context = dict(
            self.admin_site.each_context(request),
            total=total,
            by_status=json.dumps(by_status, ensure_ascii=False),
            total_sum=total_sum,
            top_clients=top_clients,
            month_labels=json.dumps(month_labels, ensure_ascii=False),
            month_counts=json.dumps(month_counts, ensure_ascii=False),
            opts=self.model._meta,
            title='Аналитика по заявкам',
        )
        from django.shortcuts import render
        return render(request, 'admin/rentals/rentalapplication/analytics.html', context)

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
    list_display = ('full_name', 'phone_number', 'get_passport_info', 'get_rental_count', 'get_last_rental_date', 'created_at')
    search_fields = ('full_name', 'phone_number', 'passport_number')
    ordering = ('phone_number',)
    
    def get_passport_info(self, obj):
        if obj.passport_number:
            return f"Паспорт: {obj.passport_number}"
        return "Паспорт не указан"
    get_passport_info.short_description = 'Паспортные данные'
    
    def get_rental_count(self, obj):
        return obj.rental_applications.count()
    get_rental_count.short_description = 'Количество заявок'
    
    def get_last_rental_date(self, obj):
        last_rental = obj.rental_applications.order_by('-rental_start_date').first()
        if last_rental:
            return last_rental.rental_start_date
        return '-'
    get_last_rental_date.short_description = 'Последняя аренда'

    def create_rental_for_client(self, request, queryset):
        from django.shortcuts import redirect
        from urllib.parse import quote
        
        if queryset.count() == 1:
            # Если выбран только один клиент, перенаправляем на форму создания
            client = queryset.first()
            
            # Формируем URL с предзаполненными данными клиента, включая паспортные данные
            params = {
                'client_id': client.id,
                'full_name': quote(client.full_name),
                'phone_number': quote(str(client.phone_number)),
            }
            
            # Добавляем паспортные данные, если они есть
            if client.passport_number:
                params['passport_number'] = quote(client.passport_number)
            if client.passport_issued_by:
                params['passport_issued_by'] = quote(client.passport_issued_by)
            if client.passport_issue_date:
                params['passport_issue_date'] = client.passport_issue_date.strftime('%Y-%m-%d')
            # Добавляем how_did_you_find_us, если есть
            if client.how_did_you_find_us:
                params['how_did_you_find_us'] = quote(client.how_did_you_find_us)
            
            # Собираем URL с параметрами
            param_string = '&'.join([f'{k}={v}' for k, v in params.items()])
            add_url = f'/admin/rentals/rentalapplication/add/?{param_string}'
            
            return redirect(add_url)
        else:
            # Если выбрано несколько клиентов, показываем сообщение
            self.message_user(request, 'Для создания заявки выберите только одного клиента', level='WARNING')
            return None
    
    create_rental_for_client.short_description = "Создать заявку для выбранного клиента"

    actions = ['create_rental_for_client']

    fieldsets = (
        ('Основная информация', {
            'fields': ('full_name', 'phone_number', 'how_did_you_find_us')
        }),
        ('Паспортные данные', {
            'fields': ('passport_number', 'passport_issued_by', 'passport_issue_date'),
            'classes': ('collapse',)
        }),
        ('История заявок', {
            'fields': ('get_rental_history',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('get_rental_history',)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:client_id>/create-rental/',
                self.admin_site.admin_view(self.create_rental_view),
                name='rentals_client_create_rental',
            ),
            path('analytics/', self.admin_site.admin_view(self.analytics_view), name='client_analytics'),
        ]
        return custom_urls + urls

    def create_rental_view(self, request, client_id):
        from django.shortcuts import redirect
        from django.contrib import messages
        
        try:
            client = Client.objects.get(id=client_id)
            
            # Формируем URL с предзаполненными данными клиента, включая паспортные данные
            params = {
                'client_id': client.id,
                'full_name': quote(client.full_name),
                'phone_number': quote(str(client.phone_number)),
            }
            
            # Добавляем паспортные данные, если они есть
            if client.passport_number:
                params['passport_number'] = quote(client.passport_number)
            if client.passport_issued_by:
                params['passport_issued_by'] = quote(client.passport_issued_by)
            if client.passport_issue_date:
                params['passport_issue_date'] = client.passport_issue_date.strftime('%Y-%m-%d')
            # Добавляем how_did_you_find_us, если есть
            if client.how_did_you_find_us:
                params['how_did_you_find_us'] = quote(client.how_did_you_find_us)
            
            # Собираем URL с параметрами
            param_string = '&'.join([f'{k}={v}' for k, v in params.items()])
            add_url = f'/admin/rentals/rentalapplication/add/?{param_string}'
            
            return redirect(add_url)
            
        except Client.DoesNotExist:
            messages.error(request, 'Клиент не найден')
            return redirect('/admin/rentals/client/')
        except Exception as e:
            messages.error(request, f'Ошибка при создании заявки: {str(e)}')
            return redirect('/admin/rentals/client/')

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
                        <a href="/admin/rentals/rentalapplication/{rental.id}/change/" class="button" style=" background: #417690; color: white; text-decoration: none; border-radius: 4px;">Просмотр</a>
                    </td>
                </tr>
            '''
        
        html += '</table>'
        
        # Добавляем кнопку создания новой заявки
        create_button = f'''
            <div style="margin-top: 15px; padding: 10px; background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 4px;">
                <a href="/admin/rentals/client/{obj.id}/create-rental/" 
                   class="button" 
                   style=" background: #28a745; color: white; text-decoration: none; border-radius: 4px; font-weight: bold;">
                    ➕ Создать новую заявку
                </a>
            </div>
        '''
        
        return format_html(html + create_button)
    get_rental_history.short_description = 'История заявок'

    def analytics_view(self, request):
        from django.db.models import Count
        from .models import Client
        import datetime
        import json
        # Всего клиентов
        total = Client.objects.count()
        # С паспортом
        with_passport = Client.objects.exclude(passport_number__isnull=True).exclude(passport_number='').count()
        # Топ-10 по количеству заявок
        top_clients = Client.objects.annotate(num=Count('rental_applications')).order_by('-num')[:10]
        # Динамика по месяцам (количество новых клиентов)
        months = []
        now = datetime.date.today()
        for i in range(11, -1, -1):
            month = (now.replace(day=1) - datetime.timedelta(days=30*i)).replace(day=1)
            months.append(month)
        month_labels = [m.strftime('%Y-%m') for m in months]
        month_counts = [Client.objects.filter(created_at__year=m.year, created_at__month=m.month).count() for m in months]
        context = dict(
            self.admin_site.each_context(request),
            total=total,
            with_passport=with_passport,
            top_clients=top_clients,
            month_labels=json.dumps(month_labels, ensure_ascii=False),
            month_counts=json.dumps(month_counts, ensure_ascii=False),
            opts=self.model._meta,
            title='Аналитика по клиентам',
        )
        from django.shortcuts import render
        return render(request, 'admin/rentals/client/analytics.html', context)

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
        
        # Получаем статистику по статусам заявок
        from django.db.models import Count
        status_stats = RentalApplication.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Формируем статистику для отображения
        stats = {}
        total_rentals = 0
        for stat in status_stats:
            status_display = dict(RentalApplication.STATUS_CHOICES).get(stat['status'], stat['status'])
            stats[stat['status']] = {
                'count': stat['count'],
                'display': status_display
            }
            total_rentals += stat['count']
        
        context = {
            'transports': transports,
            'title': 'Календарь аренды',
            'opts': Calendar._meta,
            'stats': stats,
            'total_rentals': total_rentals,
        }
        return render(request, 'admin/calendar.html', context)

    @staticmethod
    def calendar_events(request):
        try:
            transport_id = request.GET.get('transport_id')
            transport_ids = request.GET.getlist('transport_ids[]')  # Для множественного выбора
            start = request.GET.get('start')
            end = request.GET.get('end')

            # Определяем фильтр для транспорта
            if transport_ids:
                # Если переданы ID нескольких транспортов
                events = Calendar.objects.filter(transport_id__in=transport_ids)
            elif not transport_id or transport_id == 'all':
                # Если transport_id не указан или равен "all", показываем все события
                events = Calendar.objects.all()
            else:
                # Фильтруем по одному транспорту
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

                # Добавляем информацию о транспорте в заголовок события
                title = f"{event.title} (№{event.transport.number} - {event.transport.name} {event.transport.model})"

                # Получаем дополнительную информацию о заявке для tooltip
                extended_props = {
                    'transport': f"№{event.transport.number} - {event.transport.name} {event.transport.model}",
                    'transportNumber': event.transport.number,
                    'transportId': event.transport.id,
                    'status': event.status,
                    'statusDisplay': dict(RentalApplication.STATUS_CHOICES).get(event.status, event.status),
                }

                # Добавляем информацию о стоимости и депозите, если есть связанная заявка
                if event.rental_application:
                    rental = event.rental_application
                    extended_props.update({
                        'clientName': rental.full_name,
                        'clientPhone': str(rental.phone_number),
                        'cost': f"{rental.calculate_total_cost():,}",
                        'deposit': f"{int(rental.security_deposit or 0):,}",
                        'discount': f"{rental.discount}%",
                        'dailyRate': f"{rental.get_daily_rate():,}",
                        'rentalDays': rental.get_rental_days(),
                    })

                events_data.append({
                    'id': event.rental_application.id if event.rental_application else event.id,
                    'title': title,
                    'start': event.start.isoformat(),
                    'end': event.end.isoformat(),
                    'allDay': event.all_day,
                    'color': color,
                    'url': f'/admin/rentals/rentalapplication/{event.rental_application.id}/change/' if event.rental_application else None,
                    'extendedProps': extended_props,
                })

            return JsonResponse(events_data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_calendar_link'] = True
        return super().changelist_view(request, extra_context=extra_context)

@staff_member_required
def return_calendar_view(request):
    from .models import Transport, Calendar
    transports = Transport.objects.all()
    context = {
        'transports': transports,
        'title': 'Календарь сдачи транспорта',
        'opts': Calendar._meta,
    }
    return render(request, 'admin/calendar_returns.html', context)

@staff_member_required
def return_calendar_events(request):
    from .models import Calendar, RentalApplication
    try:
        transport_id = request.GET.get('transport_id')
        start = request.GET.get('start')
        end = request.GET.get('end')

        events = Calendar.objects.all()
        if transport_id and transport_id != 'all':
            events = events.filter(transport_id=transport_id)
        if start:
            from datetime import datetime
            start_date = datetime.strptime(start.split('T')[0], '%Y-%m-%d')
            events = events.filter(end__date__gte=start_date.date())
        if end:
            from datetime import datetime
            end_date = datetime.strptime(end.split('T')[0], '%Y-%m-%d')
            events = events.filter(end__date__lte=end_date.date())

        events_data = []
        for event in events:
            color = {
                RentalApplication.STATUS_RESERVED: '#ffc107',
                RentalApplication.STATUS_ACTIVE: '#28a745',
                RentalApplication.STATUS_COMPLETED: '#17a2b8',
                RentalApplication.STATUS_CANCELLED: '#dc3545',
            }.get(event.status, '#6c757d')
            title = f"Возврат: №{event.transport.number} - {event.transport.name} {event.transport.model} ({event.title})"
            events_data.append({
                'id': event.rental_application.id if event.rental_application else event.id,
                'title': title,
                'start': event.end.isoformat(),
                'end': event.end.isoformat(),
                'allDay': True,
                'color': color,
                'url': f'/admin/rentals/rentalapplication/{event.rental_application.id}/change/' if event.rental_application else None,
                'extendedProps': {
                    'transport': f"№{event.transport.number} - {event.transport.name} {event.transport.model}",
                    'transportNumber': event.transport.number,
                    'status': event.status,
                }
            })
        return JsonResponse(events_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)