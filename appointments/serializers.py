from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, date, time
from .models import Service, Appointment


class ServiceSerializer(serializers.ModelSerializer):
    """
    Serializer para listagem e detalhes dos serviços.
    No MVP, a duração é padronizada em 60 minutos (horários fixos).
    """
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'duration_minutes', 'is_active']

    def validate_duration_minutes(self, value):
        if value != 60:
            raise serializers.ValidationError("Para o MVP com horários fixos, a duração deve ser de 60 minutos.")
        return value


class AppointmentSerializer(serializers.ModelSerializer):
    """
    Serializer para listagem e criação de agendamentos.
    O cliente é sempre preenchido com o usuário autenticado.
    """
    service_name = serializers.ReadOnlyField(source='service.name')
    service_price = serializers.ReadOnlyField(source='service.price')
    client_username = serializers.ReadOnlyField(source='client.username')
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id',
            'client',
            'client_username',
            'service',
            'service_name',
            'service_price',
            'date',
            'time',
            'status',
            'status_display',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'client', 'status', 'status_display', 'created_at', 'updated_at']
        validators = []  # Delega validação ao método validate() customizado e à UniqueConstraint do banco

    def validate_service(self, value):
        """Valida se o serviço está ativo para novos agendamentos."""
        if not value.is_active:
            raise serializers.ValidationError("Este serviço não está disponível para novos agendamentos.")
        return value

    def validate(self, attrs):
        """
        Validações de regras de negócio para criação de agendamento:
        1. Horário de funcionamento: Segunda a Sexta.
        2. Horário de início entre 09:00 e 17:00 (para encerrar até as 18:00 com 60 min de duração).
        3. Bloqueio de datas e horários passados.
        4. Bloqueio de slots já ocupados por agendamentos ativos.
        """
        appointment_date = attrs.get('date')
        appointment_time = attrs.get('time')

        if not appointment_date or not appointment_time:
            return attrs

        # 1. Validação de dia da semana (Segunda = 0, Domingo = 6)
        if appointment_date.weekday() in (5, 6):
            raise serializers.ValidationError({"date": "Atendimentos ocorrem apenas de segunda a sexta-feira."})

        # 2. Validação de horário de funcionamento (09:00 às 17:00 como início)
        start_hour = time(9, 0)
        end_hour = time(17, 0)
        if appointment_time < start_hour or appointment_time > end_hour:
            raise serializers.ValidationError({
                "time": "O horário de início deve ser entre 09:00 e 17:00 (expediente encerra às 18:00)."
            })

        # 3. Validação de data/hora no passado
        now = timezone.localtime(timezone.now())
        appointment_dt = timezone.make_aware(
            datetime.combine(appointment_date, appointment_time),
            timezone.get_current_timezone()
        )
        if appointment_dt < now:
            raise serializers.ValidationError("Não é possível agendar para uma data ou horário no passado.")

        # 4. Validação de conflito de horário (agendamento ativo existente)
        active_conflict = Appointment.objects.filter(
            date=appointment_date,
            time=appointment_time
        ).exclude(status='cancelled').exists()

        if active_conflict:
            raise serializers.ValidationError({"time": "Este horário já está ocupado."})

        return attrs


class AppointmentStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer restrito para alteração de status por administradores/prestador com máquina de estados finita:
    - pending → confirmed ou cancelled
    - confirmed → completed ou cancelled
    - completed → nenhum (estado terminal)
    - cancelled → nenhum (estado terminal)
    """
    VALID_TRANSITIONS = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['completed', 'cancelled'],
        'completed': [],
        'cancelled': [],
    }

    class Meta:
        model = Appointment
        fields = ['status']

    def validate_status(self, new_status):
        current_status = self.instance.status if self.instance else None
        if not current_status:
            return new_status

        allowed = self.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise serializers.ValidationError(
                f"Transição inválida: não é permitido alterar status de '{current_status}' para '{new_status}'."
            )
        return new_status
