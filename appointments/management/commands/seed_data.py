from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, time
from decimal import Decimal

from appointments.models import Service, Appointment


class Command(BaseCommand):
    help = "Popula o banco de dados com servicos, usuarios de demonstracao e agendamentos de teste."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Limpa os agendamentos e servicos existentes antes de criar os dados de teste.'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Inicializando Carga de Dados (Seed Data) ==="))

        if options['reset']:
            self.stdout.write(self.style.WARNING("Resetando agendamentos e servicos existentes..."))
            Appointment.objects.all().delete()
            Service.objects.all().delete()

        # 1. Criacao dos Usuarios de Teste
        self.stdout.write("-> Criando/Verificando usuarios de demonstracao...")

        admin_user, created_admin = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@barbercare.com',
                'first_name': 'Administrador',
                'last_name': 'Staff',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created_admin:
            admin_user.set_password('AdminPassword123!')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("  [+] Superusuario / Prestador criado: admin / AdminPassword123!"))
        else:
            self.stdout.write("  [*] Usuario admin ja existe.")

        client_user1, created_c1 = User.objects.get_or_create(
            username='cliente',
            defaults={
                'email': 'cliente@exemplo.com',
                'first_name': 'Joao',
                'last_name': 'Silva',
                'is_staff': False,
            }
        )
        if created_c1:
            client_user1.set_password('ClientePassword123!')
            client_user1.save()
            self.stdout.write(self.style.SUCCESS("  [+] Cliente 1 criado: cliente / ClientePassword123!"))
        else:
            self.stdout.write("  [*] Usuario cliente ja existe.")

        client_user2, created_c2 = User.objects.get_or_create(
            username='carlos',
            defaults={
                'email': 'carlos@exemplo.com',
                'first_name': 'Carlos',
                'last_name': 'Eduardo',
                'is_staff': False,
            }
        )
        if created_c2:
            client_user2.set_password('ClientePassword123!')
            client_user2.save()
            self.stdout.write(self.style.SUCCESS("  [+] Cliente 2 criado: carlos / ClientePassword123!"))
        else:
            self.stdout.write("  [*] Usuario carlos ja existe.")

        # 2. Criacao do Catalogo de Servicos
        self.stdout.write("\n-> Criando/Verificando catalogo de servicos...")

        services_data = [
            {
                'name': 'Corte Tradicional Masculino',
                'description': 'Corte com tesoura e maquina, finalizacao com pomada modeladora.',
                'price': Decimal('45.00'),
                'duration_minutes': 60,
                'is_active': True,
            },
            {
                'name': 'Barba Terapia com Toalha Quente',
                'description': 'Modelagem e hidratacao de barba com aplicacao de oleos essenciais e toalha quente.',
                'price': Decimal('35.00'),
                'duration_minutes': 60,
                'is_active': True,
            },
            {
                'name': 'Combo Cabelo + Barba Premium',
                'description': 'Atendimento completo: corte de cabelo estilizado e barba terapia.',
                'price': Decimal('70.00'),
                'duration_minutes': 60,
                'is_active': True,
            },
            {
                'name': 'Acabamento & Pezinho',
                'description': 'Alinhamento de contorno, costeletas e acabamento na navalha.',
                'price': Decimal('20.00'),
                'duration_minutes': 60,
                'is_active': True,
            },
            {
                'name': 'Tratamento Capilar & Hidratacao',
                'description': 'Lavagem especial com shampoo antiqueda e mascara de hidratacao profunda.',
                'price': Decimal('60.00'),
                'duration_minutes': 60,
                'is_active': True,
            },
        ]

        created_services = []
        for s_data in services_data:
            service, created = Service.objects.get_or_create(
                name=s_data['name'],
                defaults=s_data
            )
            created_services.append(service)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Servico criado: {service.name} (R$ {service.price:.2f})"))
            else:
                self.stdout.write(f"  [*] Servico ja existe: {service.name}")

        # 3. Criacao de Agendamentos de Demonstracao
        self.stdout.write("\n-> Criando agendamentos de demonstracao...")

        today = timezone.localdate()
        
        # Encontra o proximo dia util (Segunda a Sexta)
        next_weekday = today + timedelta(days=1)
        while next_weekday.weekday() in (5, 6):  # 5=Sabado, 6=Domingo
            next_weekday += timedelta(days=1)

        future_weekday_2 = next_weekday + timedelta(days=1)
        while future_weekday_2.weekday() in (5, 6):
            future_weekday_2 += timedelta(days=1)

        sample_appointments = [
            {
                'client': client_user1,
                'service': created_services[0],
                'date': next_weekday,
                'time': time(10, 0),
                'status': 'confirmed',
                'notes': 'Cliente prefere corte degrade baixo.',
            },
            {
                'client': client_user2,
                'service': created_services[1],
                'date': next_weekday,
                'time': time(14, 0),
                'status': 'pending',
                'notes': 'Primeira vez no estabelecimento.',
            },
            {
                'client': client_user1,
                'service': created_services[2],
                'date': future_weekday_2,
                'time': time(15, 0),
                'status': 'confirmed',
                'notes': 'Combo completo antes do final de semana.',
            },
        ]

        for appt_data in sample_appointments:
            appt, created = Appointment.objects.get_or_create(
                date=appt_data['date'],
                time=appt_data['time'],
                defaults=appt_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [+] Agendamento criado: {appt.date} as {appt.time.strftime('%H:%M')} "
                        f"- {appt.client.username} ({appt.service.name}) [{appt.status}]"
                    )
                )
            else:
                self.stdout.write(f"  [*] Agendamento ja existente no slot {appt.date} {appt.time.strftime('%H:%M')}")

        self.stdout.write(self.style.SUCCESS("\n[OK] Base de dados populada com sucesso!"))
        self.stdout.write("\n========================================================")
        self.stdout.write("CREDENCIAIS DE ACESSO PARA TESTES:")
        self.stdout.write("  * Prestador / Staff:  admin   / AdminPassword123!")
        self.stdout.write("  * Cliente 1:          cliente / ClientePassword123!")
        self.stdout.write("  * Cliente 2:          carlos  / ClientePassword123!")
        self.stdout.write("========================================================\n")
