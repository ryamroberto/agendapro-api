from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.authentication import SessionAuthentication
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import View, TemplateView
from datetime import datetime, date, time
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
    OpenApiResponse,
)

from .models import Service, Appointment
from .serializers import (
    ServiceSerializer,
    AppointmentSerializer,
    AppointmentStatusUpdateSerializer
)


# =====================================================================
# 1. Views de Renderização de Templates (HTML Frontend)
# =====================================================================

class HomeView(LoginRequiredMixin, View):
    """
    Dashboard raiz (/):
    - Anônimos são redirecionados para /accounts/login/ (via LoginRequiredMixin);
    - Usuários staff são redirecionados para /agenda/;
    - Clientes comuns visualizam a tela de agendamento (book.html).
    """
    def get(self, request):
        if request.user.is_staff:
            return redirect('appointments:staff_agenda')
        return render(request, 'appointments/book.html')


class MyAppointmentsView(LoginRequiredMixin, TemplateView):
    """
    Tela de visualização e cancelamento dos agendamentos do cliente autenticado.
    """
    template_name = 'appointments/my_appointments.html'


class StaffAgendaView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Painel da agenda diária e gestão de status exclusivo para o prestador/staff.
    - Usuários anônimos são redirecionados para a tela de login;
    - Clientes comuns autenticados recebem HTTP 403 Forbidden;
    - Usuários staff acessam normalmente (200 OK).
    """
    template_name = 'appointments/staff_agenda.html'

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("Acesso restrito ao prestador/staff.")


# =====================================================================
# 2. Views da API REST (Django REST Framework)
# =====================================================================

class ServiceListView(APIView):
    """
    Lista todos os serviços disponíveis.
    Clientes visualizam apenas os ativos; Administradores visualizam todos.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Listar serviços",
        description="Retorna a lista de serviços disponíveis. Clientes veem apenas serviços ativos (`is_active=True`), enquanto staff visualiza todos.",
        responses={200: ServiceSerializer(many=True)},
        tags=["Serviços"]
    )
    def get(self, request):
        if request.user.is_staff:
            services = Service.objects.all()
        else:
            services = Service.objects.filter(is_active=True)
        
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data)


class AvailableSlotsView(APIView):
    """
    Consulta os horários de início disponíveis (das 09:00 às 17:00) para a data informada.
    Parâmetro: ?date=YYYY-MM-DD
    Exclui finais de semana, horários passados e horários com agendamentos ativos.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Consultar horários disponíveis",
        description="Retorna slots horários livres de 60 min (09:00 às 17:00) para a data indicada. Bloqueia finais de semana e horários já preenchidos ou passados.",
        parameters=[
            OpenApiParameter(
                name='date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Data da consulta no formato YYYY-MM-DD',
                required=True
            )
        ],
        responses={
            200: OpenApiResponse(description="Lista de horários livres calculados com sucesso"),
            400: OpenApiResponse(description="Data ausente ou em formato inválido")
        },
        tags=["Agendamentos"]
    )
    def get(self, request):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response(
                {"error": "O parâmetro 'date' no formato YYYY-MM-DD é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Formato de data inválido. Utilize YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Finais de semana não possuem atendimento
        if target_date.weekday() in (5, 6):
            return Response({
                "date": date_str,
                "available_slots": [],
                "message": "Não há atendimento aos finais de semana."
            })

        # Horários fixos de início (09:00 até 17:00, para serviços de 60 min encerrarem até 18:00)
        all_hours = [time(hour, 0) for hour in range(9, 18)]
        now = timezone.localtime(timezone.now())

        # Busca horários já ocupados no banco para esta data
        booked_times = set(
            Appointment.objects.filter(
                date=target_date
            ).exclude(status='cancelled').values_list('time', flat=True)
        )

        available_slots = []
        for slot in all_hours:
            # 1. Verifica se já está ocupado
            if slot in booked_times:
                continue

            # 2. Se for hoje, verifica se já passou do horário atual
            slot_dt = timezone.make_aware(
                datetime.combine(target_date, slot),
                timezone.get_current_timezone()
            )
            if slot_dt <= now:
                continue

            available_slots.append(slot.strftime('%H:%M'))

        return Response({
            "date": date_str,
            "available_slots": available_slots
        })


class AppointmentListCreateView(APIView):
    """
    GET: Lista os agendamentos (o cliente vê os seus; o prestador/staff vê todos).
    POST: Cria um novo agendamento para o usuário autenticado com controle de concorrência.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Listar agendamentos",
        description="Retorna a lista de agendamentos. Clientes veem apenas os seus próprios. Staff visualiza todos com suporte a filtros por data e status.",
        parameters=[
            OpenApiParameter(name='date', type=OpenApiTypes.DATE, location=OpenApiParameter.QUERY, description='Filtro por data YYYY-MM-DD (apenas staff)'),
            OpenApiParameter(name='status', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Filtro por status: pending, confirmed, completed, cancelled (apenas staff)')
        ],
        responses={200: AppointmentSerializer(many=True)},
        tags=["Agendamentos"]
    )
    def get(self, request):
        if request.user.is_staff:
            appointments = Appointment.objects.select_related('service', 'client').all()
            date_filter = request.query_params.get('date')
            status_filter = request.query_params.get('status')
            if date_filter:
                appointments = appointments.filter(date=date_filter)
            if status_filter:
                appointments = appointments.filter(status=status_filter)
        else:
            appointments = Appointment.objects.select_related('service', 'client').filter(client=request.user)

        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Criar agendamento",
        description="Cria um novo agendamento para o usuário logado com validação atômica e proteção anti-overbooking.",
        request=AppointmentSerializer,
        responses={
            201: AppointmentSerializer,
            400: OpenApiResponse(description="Horário ocupado, data no passado ou dados inválidos")
        },
        tags=["Agendamentos"]
    )
    def post(self, request):
        serializer = AppointmentSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                appointment = serializer.save(client=request.user)
                return Response(
                    AppointmentSerializer(appointment).data,
                    status=status.HTTP_201_CREATED
                )
        except IntegrityError:
            return Response(
                {"detail": "Este horário já está ocupado por outro agendamento."},
                status=status.HTTP_400_BAD_REQUEST
            )


class AppointmentCancelView(APIView):
    """
    Permite que o dono do agendamento ou a equipe (staff) cancele um agendamento pendente/confirmado.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cancelar agendamento",
        description="Cancela um agendamento existente nos status pending ou confirmed, liberando o horário no banco.",
        request=None,
        responses={
            200: OpenApiResponse(description="Agendamento cancelado com sucesso e horário liberado"),
            400: OpenApiResponse(description="Agendamento já cancelado ou já concluído"),
            403: OpenApiResponse(description="Apenas o cliente dono ou staff pode cancelar"),
            404: OpenApiResponse(description="Agendamento não encontrado")
        },
        tags=["Agendamentos"]
    )
    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            return Response({"detail": "Agendamento não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        # Regra de permissão: Apenas o dono ou staff pode cancelar
        if not request.user.is_staff and appointment.client != request.user:
            return Response(
                {"detail": "Você não tem permissão para cancelar este agendamento."},
                status=status.HTTP_403_FORBIDDEN
            )

        if appointment.status == 'cancelled':
            return Response(
                {"detail": "Este agendamento já está cancelado."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if appointment.status == 'completed':
            return Response(
                {"detail": "Não é possível cancelar um agendamento já concluído."},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.status = 'cancelled'
        appointment.save(update_fields=['status', 'updated_at'])

        return Response({
            "detail": "Agendamento cancelado com sucesso. O horário foi liberado.",
            "appointment": AppointmentSerializer(appointment).data
        })


class AppointmentStatusUpdateView(APIView):
    """
    Permite exclusivamente ao prestador/administrador (staff) alterar o status do agendamento
    obedecendo à máquina de estados.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Atualizar status do agendamento (Staff)",
        description="Permite exclusivamente ao staff avançar o status do agendamento de acordo com a máquina de estados.",
        request=AppointmentStatusUpdateSerializer,
        responses={
            200: OpenApiResponse(description="Status atualizado com sucesso"),
            400: OpenApiResponse(description="Transição de status inválida ou erro de payload"),
            403: OpenApiResponse(description="Acesso restrito ao staff"),
            404: OpenApiResponse(description="Agendamento não encontrado")
        },
        tags=["Agendamentos"]
    )
    def patch(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            return Response({"detail": "Agendamento não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AppointmentStatusUpdateSerializer(appointment, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response({
            "detail": "Status atualizado com sucesso.",
            "appointment": AppointmentSerializer(appointment).data
        })

