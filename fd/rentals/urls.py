from django.urls import path
from . import views
from .admin import CalendarAdmin, return_calendar_view, return_calendar_events


app_name = 'rentals'

urlpatterns = [
    path('get-available-transport/', views.get_available_transport, name='get_available_transport'),
    path('get-client-info/', views.get_client_info, name='get_client_info'),
    path('admin/calendar/', CalendarAdmin.calendar_view, name='admin_calendar'),
    path('admin/calendar/events/', CalendarAdmin.calendar_events, name='admin_calendar_events'),
    path('admin/calendar/returns/', return_calendar_view, name='admin_calendar_returns'),
    path('admin/calendar/returns/events/', return_calendar_events, name='admin_calendar_return_events'),
] 