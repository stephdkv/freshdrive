from django.urls import path
from . import views
from .admin import CalendarAdmin


app_name = 'rentals'

urlpatterns = [
    path('get-available-transport/', views.get_available_transport, name='get_available_transport'),
    path('admin/calendar/', CalendarAdmin.calendar_view, name='admin_calendar'),
    path('admin/calendar/events/', CalendarAdmin.calendar_events, name='admin_calendar_events'),
] 