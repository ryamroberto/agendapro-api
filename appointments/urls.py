from django.urls import path
from .views import (
    HomeView,
    MyAppointmentsView,
    StaffAgendaView,
    ServiceListView,
    AvailableSlotsView,
    AppointmentListCreateView,
    AppointmentCancelView,
    AppointmentStatusUpdateView
)

app_name = 'appointments'

urlpatterns = [
    # Rotas de Páginas HTML (Frontend)
    path('', HomeView.as_view(), name='home'),
    path('meus-agendamentos/', MyAppointmentsView.as_view(), name='my_appointments'),
    path('agenda/', StaffAgendaView.as_view(), name='staff_agenda'),

    # Rotas da API REST (DRF)
    path('api/services/', ServiceListView.as_view(), name='service_list'),
    path('api/available-slots/', AvailableSlotsView.as_view(), name='available_slots'),
    path('api/appointments/', AppointmentListCreateView.as_view(), name='appointment_list_create'),
    path('api/appointments/<int:pk>/cancel/', AppointmentCancelView.as_view(), name='appointment_cancel'),
    path('api/appointments/<int:pk>/status/', AppointmentStatusUpdateView.as_view(), name='appointment_status_update'),
]
