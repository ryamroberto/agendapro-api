from io import StringIO
from django.core.management import call_command
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import date, time, timedelta
from rest_framework import status


from .models import Service, Appointment
from .serializers import ServiceSerializer


class AppointmentsAPITests(TestCase):
    """
    Testes de regras de negócio, serialização, validação de slots (09:00 às 17:00),
    máquina de transição de status e endpoints REST do módulo Appointments.
    """

    def setUp(self):
        self.client = Client()

        # Usuários de teste
        self.user1 = User.objects.create_user(
            username='cliente1',
            password='SenhaForte123!',
            email='cliente1@exemplo.com'
        )
        self.user2 = User.objects.create_user(
            username='cliente2',
            password='SenhaForte123!',
            email='cliente2@exemplo.com'
        )
        self.staff_user = User.objects.create_user(
            username='prestador_staff',
            password='SenhaForte123!',
            email='prestador@exemplo.com',
            is_staff=True
        )

        # Serviços de teste (60 min de duração)
        self.service_active = Service.objects.create(
            name='Corte de Cabelo',
            description='Corte tradicional',
            price=50.00,
            duration_minutes=60,
            is_active=True
        )
        self.service_inactive = Service.objects.create(
            name='Serviço Desativado',
            description='Não disponível',
            price=100.00,
            duration_minutes=60,
            is_active=False
        )

        # Calcula uma data futura garantindo que seja dia de semana (Segunda a Sexta)
        today = timezone.localdate()
        days_ahead = 7
        self.future_weekday = today + timedelta(days=days_ahead)
        while self.future_weekday.weekday() in (5, 6):  # 5=Sábado, 6=Domingo
            self.future_weekday += timedelta(days=1)

        # Calcula um próximo final de semana (Sábado)
        self.future_weekend = today + timedelta(days=1)
        while self.future_weekend.weekday() != 5:
            self.future_weekend += timedelta(days=1)

        # URLs dos endpoints
        self.services_url = reverse('appointments:service_list')
        self.available_slots_url = reverse('appointments:available_slots')
        self.appointments_url = reverse('appointments:appointment_list_create')

        # URLs das páginas HTML
        self.home_url = reverse('appointments:home')
        self.my_appointments_url = reverse('appointments:my_appointments')
        self.staff_agenda_url = reverse('appointments:staff_agenda')

    # -------------------------------------------------------------
    # 1. Testes de Listagem e Validação de Serviços
    # -------------------------------------------------------------
    def test_services_list_cliente_ve_apenas_ativos(self):
        """Cliente comum só visualiza serviços ativos."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        response = self.client.get(self.services_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Corte de Cabelo')

    def test_services_list_staff_ve_todos(self):
        """Usuário staff visualiza todos os serviços (ativos e inativos)."""
        self.client.login(username='prestador_staff', password='SenhaForte123!')
        response = self.client.get(self.services_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(len(data), 2)

    def test_service_serializer_duracao_diferente_de_60_invalida(self):
        """No MVP com slots fixos, duração diferente de 60 min é rejeitada pelo serializer."""
        serializer = ServiceSerializer(data={
            'name': 'Barba Rápida',
            'price': '30.00',
            'duration_minutes': 30,
            'is_active': True
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('duration_minutes', serializer.errors)

    # -------------------------------------------------------------
    # 2. Testes de Consulta de Horários Disponíveis
    # -------------------------------------------------------------
    def test_available_slots_dia_de_semana_limites_09_as_17(self):
        """Retorna horários de início das 09:00 às 17:00 (18:00 não é início válido) e remove ocupados."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        
        # Cria um agendamento prévio às 10:00
        Appointment.objects.create(
            client=self.user2,
            service=self.service_active,
            date=self.future_weekday,
            time=time(10, 0),
            status='pending'
        )

        response = self.client.get(f"{self.available_slots_url}?date={self.future_weekday.strftime('%Y-%m-%d')}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        slots = response.json()['available_slots']
        self.assertIn('09:00', slots)
        self.assertNotIn('10:00', slots)  # Ocupado
        self.assertIn('11:00', slots)
        self.assertIn('17:00', slots)     # Último horário válido de início
        self.assertNotIn('18:00', slots)  # 18:00 é horário de fechamento, não de início

    def test_available_slots_fim_de_semana_retorna_vazio(self):
        """Consulta em dia de fim de semana retorna lista vazia."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        response = self.client.get(f"{self.available_slots_url}?date={self.future_weekend.strftime('%Y-%m-%d')}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['available_slots'], [])

    # -------------------------------------------------------------
    # 3. Testes de Criação de Agendamento e Validações
    # -------------------------------------------------------------
    def test_criar_agendamento_com_sucesso(self):
        """Cliente cria agendamento válido e o campo client é preenchido com request.user."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        
        payload = {
            'service': self.service_active.id,
            'date': self.future_weekday.strftime('%Y-%m-%d'),
            'time': '14:00',
            'notes': 'Primeira vez no estabelecimento'
        }
        response = self.client.post(self.appointments_url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        data = response.json()
        self.assertEqual(data['client'], self.user1.id)
        self.assertEqual(data['client_username'], 'cliente1')
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(data['service_name'], 'Corte de Cabelo')

    def test_criar_agendamento_no_ultimo_horario_valido_17h(self):
        """Agendamento às 17:00 é aceito com sucesso (encerra às 18:00)."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        payload = {
            'service': self.service_active.id,
            'date': self.future_weekday.strftime('%Y-%m-%d'),
            'time': '17:00',
        }
        response = self.client.post(self.appointments_url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_criar_agendamento_as_18h_rejeitado_retorna_400(self):
        """Agendamento às 18:00 é rejeitado com 400 Bad Request pois o expediente termina às 18:00."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        payload = {
            'service': self.service_active.id,
            'date': self.future_weekday.strftime('%Y-%m-%d'),
            'time': '18:00',
        }
        response = self.client.post(self.appointments_url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('time', response.json())

    def test_criar_agendamento_com_servico_inativo_retorna_400(self):
        """Tentativa de agendar serviço inativo é recusada com 400 Bad Request."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        payload = {
            'service': self.service_inactive.id,
            'date': self.future_weekday.strftime('%Y-%m-%d'),
            'time': '14:00',
        }
        response = self.client.post(self.appointments_url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('service', response.json())

    def test_criar_agendamento_no_passado_retorna_400(self):
        """Tentativa de agendamento em data passada é recusada com 400 Bad Request."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        past_date = timezone.localdate() - timedelta(days=1)
        payload = {
            'service': self.service_active.id,
            'date': past_date.strftime('%Y-%m-%d'),
            'time': '14:00',
        }
        response = self.client.post(self.appointments_url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_criar_agendamento_no_fim_de_semana_retorna_400(self):
        """Tentativa de agendar no sábado/domingo é recusada com 400 Bad Request."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        payload = {
            'service': self.service_active.id,
            'date': self.future_weekend.strftime('%Y-%m-%d'),
            'time': '14:00',
        }
        response = self.client.post(self.appointments_url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date', response.json())

    def test_criar_agendamento_fora_do_horario_comercial_retorna_400(self):
        """Horários antes das 09:00 retornam 400 Bad Request."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        payload = {
            'service': self.service_active.id,
            'date': self.future_weekday.strftime('%Y-%m-%d'),
            'time': '08:00',
        }
        response = self.client.post(self.appointments_url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('time', response.json())

    def test_impedir_agendamento_em_horario_ocupado_retorna_400(self):
        """Tentativa de agendar em horário que já possui agendamento ativo retorna 400 com mensagem clara."""
        Appointment.objects.create(
            client=self.user1,
            service=self.service_active,
            date=self.future_weekday,
            time=time(15, 0),
            status='pending'
        )

        self.client.login(username='cliente2', password='SenhaForte123!')
        payload = {
            'service': self.service_active.id,
            'date': self.future_weekday.strftime('%Y-%m-%d'),
            'time': '15:00',
        }
        response = self.client.post(self.appointments_url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('time', response.json())

    # -------------------------------------------------------------
    # 4. Testes de Visibilidade e Isolamento de Agendamentos
    # -------------------------------------------------------------
    def test_cliente_visualiza_apenas_seus_proprios_agendamentos(self):
        """Cliente 1 só vê os agendamentos dele ao listar."""
        Appointment.objects.create(
            client=self.user1,
            service=self.service_active,
            date=self.future_weekday,
            time=time(11, 0)
        )
        Appointment.objects.create(
            client=self.user2,
            service=self.service_active,
            date=self.future_weekday,
            time=time(14, 0)
        )

        self.client.login(username='cliente1', password='SenhaForte123!')
        response = self.client.get(self.appointments_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['client_username'], 'cliente1')

    def test_staff_visualiza_todos_os_agendamentos(self):
        """Usuário staff vê agendamentos de todos os clientes."""
        Appointment.objects.create(
            client=self.user1,
            service=self.service_active,
            date=self.future_weekday,
            time=time(11, 0)
        )
        Appointment.objects.create(
            client=self.user2,
            service=self.service_active,
            date=self.future_weekday,
            time=time(14, 0)
        )

        self.client.login(username='prestador_staff', password='SenhaForte123!')
        response = self.client.get(self.appointments_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(len(data), 2)

    # -------------------------------------------------------------
    # 5. Testes de Cancelamento e Máquina de Estados de Status
    # -------------------------------------------------------------
    def test_cliente_cancela_seu_proprio_agendamento(self):
        """Cliente consegue cancelar o próprio agendamento e o status muda para 'cancelled'."""
        appt = Appointment.objects.create(
            client=self.user1,
            service=self.service_active,
            date=self.future_weekday,
            time=time(16, 0),
            status='pending'
        )

        self.client.login(username='cliente1', password='SenhaForte123!')
        cancel_url = reverse('appointments:appointment_cancel', kwargs={'pk': appt.id})
        response = self.client.post(cancel_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'cancelled')

    def test_cliente_nao_pode_cancelar_agendamento_de_outro_cliente(self):
        """Cliente 2 recebe 403 Forbidden ao tentar cancelar agendamento do Cliente 1."""
        appt = Appointment.objects.create(
            client=self.user1,
            service=self.service_active,
            date=self.future_weekday,
            time=time(16, 0),
            status='pending'
        )

        self.client.login(username='cliente2', password='SenhaForte123!')
        cancel_url = reverse('appointments:appointment_cancel', kwargs={'pk': appt.id})
        response = self.client.post(cancel_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'pending')

    def test_transicoes_validas_de_status_por_staff(self):
        """Staff realiza transições permitidas: pending -> confirmed -> completed."""
        appt = Appointment.objects.create(
            client=self.user1,
            service=self.service_active,
            date=self.future_weekday,
            time=time(12, 0),
            status='pending'
        )
        self.client.login(username='prestador_staff', password='SenhaForte123!')
        status_url = reverse('appointments:appointment_status_update', kwargs={'pk': appt.id})

        # 1. pending -> confirmed (Válido)
        res1 = self.client.patch(status_url, {'status': 'confirmed'}, content_type='application/json')
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'confirmed')

        # 2. confirmed -> completed (Válido)
        res2 = self.client.patch(status_url, {'status': 'completed'}, content_type='application/json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'completed')

    def test_transicoes_invalidas_de_status_sao_rejeitadas(self):
        """Transições não permitidas retornam 400 Bad Request."""
        self.client.login(username='prestador_staff', password='SenhaForte123!')

        # Caso A: pending -> completed direto (Inválido)
        appt_pending = Appointment.objects.create(
            client=self.user1,
            service=self.service_active,
            date=self.future_weekday,
            time=time(13, 0),
            status='pending'
        )
        url_pending = reverse('appointments:appointment_status_update', kwargs={'pk': appt_pending.id})
        res_a = self.client.patch(url_pending, {'status': 'completed'}, content_type='application/json')
        self.assertEqual(res_a.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', res_a.json())

        # Caso B: completed -> qualquer outro status (Inválido - estado terminal)
        appt_completed = Appointment.objects.create(
            client=self.user1,
            service=self.service_active,
            date=self.future_weekday,
            time=time(14, 0),
            status='completed'
        )
        url_completed = reverse('appointments:appointment_status_update', kwargs={'pk': appt_completed.id})
        res_b = self.client.patch(url_completed, {'status': 'pending'}, content_type='application/json')
        self.assertEqual(res_b.status_code, status.HTTP_400_BAD_REQUEST)

        # Caso C: cancelled -> qualquer outro status (Inválido - estado terminal)
        appt_cancelled = Appointment.objects.create(
            client=self.user1,
            service=self.service_active,
            date=self.future_weekday,
            time=time(15, 0),
            status='cancelled'
        )
        url_cancelled = reverse('appointments:appointment_status_update', kwargs={'pk': appt_cancelled.id})
        res_c = self.client.patch(url_cancelled, {'status': 'confirmed'}, content_type='application/json')
        self.assertEqual(res_c.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------
    # 6. Testes de Páginas HTML, Redirecionamentos e Permissões
    # -------------------------------------------------------------
    def test_paginas_anonimo_redirecionam_para_login(self):
        """Usuário anônimo tentando acessar /, /meus-agendamentos/ ou /agenda/ é redirecionado para login."""
        res_home = self.client.get(self.home_url)
        self.assertEqual(res_home.status_code, status.HTTP_302_FOUND)
        self.assertIn(reverse('login'), res_home.url)

        res_my_appts = self.client.get(self.my_appointments_url)
        self.assertEqual(res_my_appts.status_code, status.HTTP_302_FOUND)
        self.assertIn(reverse('login'), res_my_appts.url)

        res_agenda = self.client.get(self.staff_agenda_url)
        self.assertEqual(res_agenda.status_code, status.HTTP_302_FOUND)
        self.assertIn(reverse('login'), res_agenda.url)

    def test_pagina_raiz_cliente_carrega_com_sucesso(self):
        """Cliente autenticado acessando / recebe 200 OK e a tela de agendamento."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'appointments/book.html')

    def test_pagina_raiz_staff_redireciona_para_agenda(self):
        """Usuário staff acessando / é redirecionado para /agenda/."""
        self.client.login(username='prestador_staff', password='SenhaForte123!')
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertRedirects(response, self.staff_agenda_url)

    def test_pagina_agenda_cliente_comum_bloqueado_com_403(self):
        """Cliente comum que tentar acessar /agenda/ recebe 403 Forbidden diretamente do servidor."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        response = self.client.get(self.staff_agenda_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pagina_agenda_staff_carrega_com_sucesso(self):
        """Usuário staff acessando /agenda/ recebe 200 OK e o template staff_agenda.html."""
        self.client.login(username='prestador_staff', password='SenhaForte123!')
        response = self.client.get(self.staff_agenda_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'appointments/staff_agenda.html')

    def test_pagina_meus_agendamentos_cliente_carrega_com_sucesso(self):
        """Cliente autenticado acessando /meus-agendamentos/ recebe 200 OK."""
        self.client.login(username='cliente1', password='SenhaForte123!')
        response = self.client.get(self.my_appointments_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'appointments/my_appointments.html')

    # -------------------------------------------------------------
    # 7. Teste do Comando Customizado de Gestão (seed_data)
    # -------------------------------------------------------------
    def test_command_seed_data_popula_base_com_sucesso(self):
        """O comando seed_data cria usuários, catálogo de serviços e agendamentos de teste."""
        out = StringIO()
        call_command('seed_data', '--reset', stdout=out)
        output_text = out.getvalue()
        self.assertIn("Base de dados populada com sucesso", output_text)
        self.assertTrue(User.objects.filter(username='admin', is_staff=True).exists())
        self.assertTrue(User.objects.filter(username='cliente').exists())
        self.assertTrue(Service.objects.filter(name='Corte Tradicional Masculino').exists())
        self.assertTrue(Appointment.objects.exists())

