from django import forms
from .models import RentalApplication, Transport
from django.db.models import Q
from datetime import datetime
from django.contrib.admin.widgets import AdminDateWidget

class RentalApplicationForm(forms.ModelForm):
    rental_start_date = forms.DateField(widget=AdminDateWidget(), help_text="Дата начала аренды", label='Дата начала аренды')
    rental_end_date = forms.DateField(widget=AdminDateWidget(), help_text="Дата окончания аренды", label='Дата окончания аренды')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Получаем выбранные даты из данных формы
        start_date = None
        end_date = None
        
        if self.data.get('rental_start_date') and self.data.get('rental_end_date'):
            try:
                # Пробуем разные форматы даты
                for date_format in ['%d.%m.%Y', '%Y-%m-%d']:
                    try:
                        start_date = datetime.strptime(self.data['rental_start_date'], date_format).date()
                        end_date = datetime.strptime(self.data['rental_end_date'], date_format).date()
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        # Если это редактирование существующей заявки
        if self.instance and self.instance.pk:
            current_transport = self.instance.transport
            # Делаем поле transport необязательным при редактировании
            self.fields['transport'].required = False
            
            # Если даты не пришли из формы, берем их из instance
            if not (start_date and end_date):
                if self.instance.rental_start_date and self.instance.rental_end_date:
                    start_date = self.instance.rental_start_date
                    end_date = self.instance.rental_end_date

            if start_date and end_date:
                # Получаем ID всех транспортных средств, у которых есть пересекающиеся брони
                # Исключаем отмененные и завершенные заявки
                booked_transport_ids = RentalApplication.objects.filter(
                    Q(rental_start_date__lte=end_date) & 
                    Q(rental_end_date__gte=start_date) &
                    ~Q(status__in=[RentalApplication.STATUS_CANCELLED, RentalApplication.STATUS_COMPLETED])  # Исключаем отмененные и завершенные заявки
                ).exclude(id=self.instance.id).values_list('transport_id', flat=True)
                
                # Фильтруем queryset для поля transport, включая текущий транспорт
                self.fields['transport'].queryset = Transport.objects.filter(
                    Q(id=current_transport.id) | ~Q(id__in=booked_transport_ids)
                )
            else:
                # Если даты не выбраны, показываем только текущий транспорт
                self.fields['transport'].queryset = Transport.objects.filter(id=current_transport.id)
        else:
            # Для новой заявки используем стандартную логику
            if start_date and end_date:
                # Получаем ID всех транспортных средств, у которых есть пересекающиеся брони
                # Исключаем отмененные и завершенные заявки
                booked_transport_ids = RentalApplication.objects.filter(
                    Q(rental_start_date__lte=end_date) & 
                    Q(rental_end_date__gte=start_date) &
                    ~Q(status__in=[RentalApplication.STATUS_CANCELLED, RentalApplication.STATUS_COMPLETED])  # Исключаем отмененные и завершенные заявки
                ).values_list('transport_id', flat=True)
                
                self.fields['transport'].queryset = Transport.objects.exclude(
                    id__in=booked_transport_ids
                )
            else:
                self.fields['transport'].queryset = Transport.objects.all()
            
        # Добавляем класс для стилизации
        if 'rental_start_date' in self.fields:
            self.fields['rental_start_date'].widget.attrs.update({'class': 'date-field vDateField'})
        if 'rental_end_date' in self.fields:
            self.fields['rental_end_date'].widget.attrs.update({'class': 'date-field vDateField'})
        if 'transport' in self.fields:
            self.fields['transport'].widget.attrs.update({'class': 'transport-field'})

    def clean(self):
        cleaned_data = super().clean()
        # Если это редактирование существующей заявки и транспорт не выбран,
        # используем текущий транспорт из instance
        if self.instance and self.instance.pk:
            if not cleaned_data.get('transport'):
                cleaned_data['transport'] = self.instance.transport
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Если это редактирование и транспорт не был выбран, используем текущий
        if self.instance and self.instance.pk and not instance.transport:
            instance.transport = self.instance.transport
        if commit:
            instance.save()
        return instance

    class Meta:
        model = RentalApplication
        fields = '__all__'
        widgets = {
            'how_did_you_find_us': forms.Select(),
        } 