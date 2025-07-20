from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from .models import Transport, RentalApplication, Client
from django.db.models import Q
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@require_GET
@csrf_exempt
def get_available_transport(request):
    """View для получения списка доступного транспорта на выбранные даты"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    logger.info(f"Received request for dates: {start_date} to {end_date}")
    
    if not all([start_date, end_date]):
        return JsonResponse({
            'status': 'error',
            'message': 'Укажите даты аренды'
        })
    
    try:
        # Пробуем разные форматы даты
        parsed_dates = False
        for date_format in ['%d.%m.%Y', '%Y-%m-%d']:
            try:
                start_date = datetime.strptime(start_date, date_format).date()
                end_date = datetime.strptime(end_date, date_format).date()
                parsed_dates = True
                logger.info(f"Parsed dates: {start_date} to {end_date}")
                break
            except ValueError:
                continue
                
        if not parsed_dates:
            return JsonResponse({
                'status': 'error',
                'message': 'Неверный формат даты'
            })
        
        # Получаем ID занятого транспорта, исключая отмененные и завершенные заявки
        booked_transport_ids = RentalApplication.objects.filter(
            Q(rental_start_date__lte=end_date) & 
            Q(rental_end_date__gte=start_date) &
            ~Q(status__in=[RentalApplication.STATUS_CANCELLED, RentalApplication.STATUS_COMPLETED])  # Исключаем отмененные и завершенные заявки
        ).values_list('transport_id', flat=True)
        
        logger.info(f"Booked transport IDs: {list(booked_transport_ids)}")
        
        # Получаем доступный транспорт
        available_transport = Transport.objects.exclude(
            id__in=booked_transport_ids
        )
        
        logger.info(f"Available transport count: {available_transport.count()}")
        
        # Формируем список для выпадающего списка
        transport_options = [
            {
                'id': t.id,
                'text': f"№{t.number} {t.name} {t.model} ({t.vin_number})"
            }
            for t in available_transport
        ]
        
        logger.info(f"Returning options: {transport_options}")
        
        return JsonResponse({
            'status': 'success',
            'options': transport_options
        })
        
    except Exception as e:
        logger.error(f"Error in get_available_transport: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }) 

@require_GET
@csrf_exempt
def get_client_info(request):
    """View для получения информации о клиенте по ID"""
    client_id = request.GET.get('client_id')
    if not client_id:
        return JsonResponse({'status': 'error', 'message': 'Не передан client_id'})
    try:
        client = Client.objects.get(id=client_id)
        data = {
            'full_name': client.full_name or '',
            'phone_number': str(client.phone_number) if client.phone_number else '',
            'passport_number': client.passport_number or '',
            'passport_issued_by': client.passport_issued_by or '',
            'passport_issue_date': client.passport_issue_date.strftime('%Y-%m-%d') if client.passport_issue_date else '',
            'how_did_you_find_us': client.how_did_you_find_us or '',
        }
        return JsonResponse({'status': 'success', 'data': data})
    except Client.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Клиент не найден'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}) 