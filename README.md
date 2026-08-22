# AgendaPro API — Sistema de Agendamento e Gestao de Servicos

Plataforma para agendamento de servicos em tempo real desenvolvida com Django, Django REST Framework (DRF), autenticacao por sessao (SessionAuthentication com cookies HttpOnly e protecao CSRF) e interface web responsiva com JavaScript nativo.

---

## Arquitetura e Decisoes Tecnicas

O projeto adota a arquitetura monolitica integrada, combinando renderizacao no servidor (Django Templates) com consumo de endpoints da REST API:

- **Autenticacao por Sessao (SessionAuthentication) e Seguranca:**
  - Evita o armazenamento de credenciais e tokens em `localStorage`.
  - O cookie de sessao (`sessionid`) utiliza a flag `HttpOnly`, impedindo a leitura via scripts do navegador.
  - Protecao nativa contra CSRF com validacao de token `X-CSRFToken` e `credentials: 'same-origin'` em operacoes de escrita (`POST`, `PATCH`, `DELETE`).
  - *Nota Tecnica:* Essa arquitetura reduz a superficie de exposicao a ataques de exfiltracao de credenciais e forjamento de requisicoes (CSRF), mantendo a sanitizacao e escape de dados no servidor contra XSS.
- **Frontend Nativo:** Construido com HTML5 semantico, CSS modular com Design Tokens e JavaScript assincrono sem frameworks pesados.
- **Transacoes e Concorrencia:** Criacao de agendamentos protegida por transacao atomica (`transaction.atomic()`) e restricao no banco de dados (`UniqueConstraint`) para evitar conflito de horarios.

---

## Perfis de Acesso e Permissoes

### 1. Cliente (`is_staff = False`)
- Acesso a tela de agendamento (`/`).
- Consulta ao catalogo de servicos ativos e slots de horarios livres em tempo real.
- Criacao de agendamentos vinculados a sua conta.
- Visualizacao e cancelamento exclusivo dos seus proprios agendamentos (`/meus-agendamentos/`).
- Bloqueio no servidor para rotas restritas e administrativas (`403 Forbidden`).

### 2. Prestador de Servicos / Staff (`is_staff = True`)
- Redirecionamento pos-login para o painel operacional da agenda (`/agenda/`).
- Visualizacao da grade completa de atendimentos com filtros por data.
- Gestao de status do agendamento (Confirmar, Concluir, Cancelar).
- Acesso ao painel administrativo do Django (`/admin/`) para gestao de catalogo e usuarios.

---

## Regras de Negocio e Validacoes

1. **Horario de Funcionamento:**
   - Atendimentos de segunda a sexta-feira.
   - Slots validos: 09:00 as 17:00 (intervalos de 60 minutos), garantindo encerramento do expediente ate as 18:00.
2. **Prevencao de Agendamento Retroativo:**
   - Bloqueio de datas e horarios no passado com base no fuso horario `America/Sao_Paulo`.
3. **Controle Anti-Overbooking:**
   - Validacao no front-end (desabilitando horarios ocupados), no serializer do DRF e no banco de dados via `UniqueConstraint`.
4. **Liberacao de Horarios:**
   - Agendamentos cancelados liberam imediatamente o slot para novas reservas.
5. **Maquina de Estados de Status:**
   - `pending` (Pendente) -> `confirmed` (Confirmado) ou `cancelled` (Cancelado)
   - `confirmed` (Confirmado) -> `completed` (Concluido) ou `cancelled` (Cancelado)
   - `completed` (Concluido) -> Estado terminal (imutavel)
   - `cancelled` (Cancelado) -> Estado terminal (imutavel)

---

## Rotas e Endpoints

### Rotas Web (HTML)

| Metodo | URL | Permissao | Descricao |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | `IsAuthenticated` | Tela de agendamento (redireciona staff para `/agenda/`). |
| `GET` | `/meus-agendamentos/` | `IsAuthenticated` | Historico e cancelamento de agendamentos do cliente. |
| `GET` | `/agenda/` | `IsAdminUser` (Staff) | Painel operacional do prestador com gestao de status. |
| `GET`/`POST` | `/accounts/login/` | `AllowAny` | Formulario de login com protecao CSRF. |
| `POST` | `/accounts/logout/` | `IsAuthenticated` | Encerramento de sessao via POST. |

### Endpoints da API REST (DRF)

| Metodo | Endpoint | Permissao | Descricao / Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/docs/` | `AllowAny` | Documentacao interativa via Swagger UI (OpenAPI 3.0). |
| `GET` | `/api/redoc/` | `AllowAny` | Documentacao tecnica via Redoc. |
| `GET` | `/api/schema/` | `AllowAny` | Especificacao OpenAPI em YAML/JSON. |
| `GET` | `/api/services/` | `IsAuthenticated` | Catalogo de servicos. |
| `GET` | `/api/available-slots/?date=YYYY-MM-DD` | `IsAuthenticated` | Lista de horarios disponiveis na data informada. |
| `GET` | `/api/appointments/` | `IsAuthenticated` | Lista agendamentos do cliente (ou todos para staff). |
| `POST` | `/api/appointments/` | `IsAuthenticated` | Criacao de agendamento: `{"service": 1, "date": "...", "time": "...", "notes": "..."}` |
| `POST` | `/api/appointments/<id>/cancel/` | Dono ou Staff | Cancelamento de agendamento. |
| `PATCH` | `/api/appointments/<id>/status/` | `IsAdminUser` (Staff) | Atualizacao de status: `{"status": "confirmed" \| "completed" \| "cancelled"}` |
| `GET` | `/api/me/` | `IsAuthenticated` | Dados do usuario autenticado. |

---

## Instalacao e Execucao Local

### Pre-requisitos
- Python 3.10+ instalado.
- Git instalado.

### 1. Clonar o repositorio e acessar a pasta
```bash
git clone <url-do-repositorio>
cd projeto
```

### 2. Criar e ativar o ambiente virtual
```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Configurar as variaveis de ambiente
Copie o arquivo de exemplo `.env.example` para `.env`:
```bash
cp .env.example .env
```

### 4. Instalar as dependencias
```bash
pip install -r requirements.txt
```

### 5. Executar as migracoes do banco de dados
```bash
python manage.py migrate
```

### 6. Popular o banco com dados de demonstracao (Seed Data)
Execute o comando para carregar catalogo de servicos, usuarios de teste e agendamentos:
```bash
python manage.py seed_data --reset
```

### 7. Iniciar o servidor de desenvolvimento
```bash
python manage.py runserver
```

Acesse a aplicacao no navegador em: `http://127.0.0.1:8000/`  
Acesse a documentacao Swagger em: `http://127.0.0.1:8000/api/docs/`

---

### Credenciais Pre-configuradas para Testes

| Perfil | Usuario | Senha | Acesso / Painel |
| :--- | :--- | :--- | :--- |
| **Prestador / Staff (Admin)** | `admin` | `AdminPassword123!` | `/agenda/` e `/admin/` |
| **Cliente Padrao 1** | `cliente` | `ClientePassword123!` | `/` e `/meus-agendamentos/` |
| **Cliente Padrao 2** | `carlos` | `ClientePassword123!` | `/` e `/meus-agendamentos/` |

---

## Suite de Testes Automatizados

O projeto conta com **35 testes automatizados** cobrindo autenticacao, documentacao OpenAPI, integridade do banco de dados, maquina de estados, endpoints REST, comando de carga de dados e controle de acesso a paginas.

Para rodar todos os testes:
```bash
python manage.py test
```

### Cobertura dos Testes:
- **Autenticacao e Documentacao (`core` — 9 testes):**
  - Bloqueio anonimo, login, credenciais invalidas, consulta de dados do usuario e revogacao pos-logout.
  - Validacao da especificacao OpenAPI em `/api/schema/` (YAML e JSON).
  - Disponibilidade das interfaces Swagger UI e Redoc.
- **Dominio, Slots, Validacoes e Carga (`appointments` — 20 testes):**
  - Listagem de servicos ativos vs inativos conforme perfil.
  - Validacao da duracao padrao de 60 minutos.
  - Calculo de slots disponiveis entre 09:00 e 17:00.
  - Bloqueio de agendamentos em fins de semana e no passado.
  - Bloqueio de inicio as 18:00 (horario de fechamento).
  - Prevencao de agendamentos duplicados (anti-overbooking).
  - Isolamento de visibilidade por cliente logado.
  - Cancelamento pelo cliente e bloqueio de cancelamento por terceiros (`403 Forbidden`).
  - Transicoes validas e rejeicao de transicoes invalidas de status.
  - Execucao e integridade do comando de gestao `seed_data`.
- **Controle de Acesso a Paginas HTML (`appointments` — 6 testes):**
  - Redirecionamento de usuarios anonimos para login.
  - Acesso de cliente comum a `/` carrega a tela de agendamento (`200 OK`).
  - Acesso de staff a `/` redireciona para `/agenda/` (`302 Found`).
  - Bloqueio no servidor para cliente comum em `/agenda/` (`403 Forbidden`).
  - Acesso de staff a `/agenda/` carrega a agenda (`200 OK`).
  - Acesso a `/meus-agendamentos/` carrega com sucesso (`200 OK`).

---

## Estrutura do Projeto

```
projeto/
├── config/                     # Configuracoes do Django e rotas raiz
│   ├── asgi.py
│   ├── settings.py             # Configuracoes com Decouple (.env), SessionAuth e CSRF
│   ├── urls.py                 # Roteamento central e documentacao OpenAPI
│   └── wsgi.py
├── core/                       # App base de autenticacao e utilitarios
│   ├── apps.py
│   ├── tests.py                # Testes de autenticacao, sessao e OpenAPI
│   ├── urls.py
│   └── views.py                # Endpoint /api/me/
├── appointments/               # App de dominio (Agendamentos e Servicos)
│   ├── admin.py                # Registro no Django Admin
│   ├── apps.py
│   ├── management/             # Comandos customizados do Django
│   │   └── commands/
│   │       └── seed_data.py    # Comando de carga inicial para demonstracao
│   ├── migrations/             # Migracoes do banco de dados
│   ├── models.py               # Modelos Service e Appointment com Constraints
│   ├── serializers.py          # Serializers do DRF com validacoes de negocio
│   ├── tests.py                # Testes de API, regras, paginas e seed
│   ├── urls.py                 # Rotas HTML e da API
│   └── views.py                # TemplateViews e APIViews
├── static/                     # Arquivos estaticos
│   ├── css/
│   │   └── style.css           # Design Tokens e layout responsivo
│   └── js/
│       ├── booking.js          # Logica do fluxo de agendamento
│       ├── csrf.js             # Utilitario de CSRF e fetch seguro
│       ├── my_appointments.js  # Historico e cancelamento
│       └── staff_agenda.js     # Painel do prestador com filtros e status
├── templates/                  # Templates Django
│   ├── base.html               # Layout base da aplicacao
│   ├── registration/
│   │   └── login.html          # Tela de login
│   └── appointments/
│       ├── book.html           # Tela de agendamento por etapas
│       ├── my_appointments.html# Tela Meus Agendamentos
│       └── staff_agenda.html   # Painel da agenda
├── .env.example                # Modelo de variaveis de ambiente
├── manage.py
├── requirements.txt            # Dependencias do projeto
├── .gitignore                  # Arquivos ignorados no versionamento
└── README.md                   # Documentacao tecnica do projeto
```

---

## Licenca

Projeto desenvolvido para fins de estudo e portfolio. Livre para uso e adaptacao.
