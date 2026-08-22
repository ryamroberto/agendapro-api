from django.db import models
from django.contrib.auth.models import User


class Service(models.Model):
    """
    Representa um serviço oferecido pelo prestador (ex: Corte de Cabelo, Barba, Consulta).
    """
    name = models.CharField(max_length=100, verbose_name="Nome do Serviço")
    description = models.TextField(blank=True, verbose_name="Descrição")
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Preço (R$)")
    duration_minutes = models.PositiveIntegerField(default=60, verbose_name="Duração (minutos)")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Serviço"
        verbose_name_plural = "Serviços"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - R$ {self.price:.2f}"


class Appointment(models.Model):
    """
    Representa o agendamento de um cliente em uma data e horário específicos.
    """
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('confirmed', 'Confirmado'),
        ('completed', 'Concluído'),
        ('cancelled', 'Cancelado'),
    ]

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name="Cliente"
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name="Serviço"
    )
    date = models.DateField(verbose_name="Data")
    time = models.TimeField(verbose_name="Horário")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    notes = models.TextField(blank=True, verbose_name="Observações")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ['-date', '-time']
        constraints = [
            # Impede conflito de horários para agendamentos ativos (não cancelados)
            models.UniqueConstraint(
                fields=['date', 'time'],
                condition=~models.Q(status='cancelled'),
                name='unique_active_appointment_per_slot'
            )
        ]

    def __str__(self):
        return f"{self.date} {self.time} - {self.client.username} ({self.service.name}) [{self.get_status_display()}]"
