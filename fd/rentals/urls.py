from django.urls import path
from . import views


app_name = 'rentals'

urlpatterns = [
    path('get-available-transport/', views.get_available_transport, name='get_available_transport'),
] 