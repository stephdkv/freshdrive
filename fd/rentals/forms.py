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
        
        if start_date and end_date:
            # Получаем ID всех транспортных средств, у которых есть пересекающиеся брони
            booked_transport_ids = RentalApplication.objects.filter(
                Q(rental_start_date__lte=end_date) & 
                Q(rental_end_date__gte=start_date)
            ).exclude(id=self.instance.id if self.instance else None).values_list('transport_id', flat=True)
            
            # Фильтруем queryset для поля transport
            self.fields['transport'].queryset = Transport.objects.exclude(
                id__in=booked_transport_ids
            )
        else:
            # Если даты не выбраны или неверного формата, показываем весь транспорт
            self.fields['transport'].queryset = Transport.objects.all()
            
        # Добавляем класс для стилизации
        self.fields['rental_start_date'].widget.attrs.update({'class': 'date-field vDateField'})
        self.fields['rental_end_date'].widget.attrs.update({'class': 'date-field vDateField'})
        self.fields['transport'].widget.attrs.update({'class': 'transport-field'})

    class Meta:
        model = RentalApplication
        fields = '__all__' 