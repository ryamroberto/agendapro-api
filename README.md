# 💈 Barber & Care — Sistema de Gestão e Agendamento Online

> Plataforma moderna para agendamento de serviços em tempo real desenvolvida com **Django**, **Django REST Framework (DRF)**, **SessionAuthentication (Cookies + CSRF)** e **JavaScript Vanilla**, seguindo princípios de **Atomic Design** e com interface desenvolvida considerando princípios de acessibilidade WCAG.

---

## 📸 Demonstração da Interface (Screenshots)

> ℹ️ *As imagens abaixo são seções reservadas (placeholders) e devem ser capturadas e incluídas após a execução da aplicação em ambiente local.*

| Tela de Agendamento (Cliente) | Painel da Agenda (Prestador / Staff) |
| :---: | :---: |
| *(Placeholder: adicione a captura de tela de `book.html`)* | *(Placeholder: adicione a captura de tela de `staff_agenda.html`)* |

| Meus Agendamentos (Histórico) | Tela de Autenticação (Login) |
| :---: | :---: |
| *(Placeholder: adicione a captura de tela de `my_appointments.html`)* | *(Placeholder: adicione a captura de tela de `login.html`)* |

---

## 🏗️ Arquitetura e Decisões de Engenharia

Este projeto adota uma arquitetura unificada (**monólito moderno**), combinando renderização no servidor com consumo dinâmico via REST API:

- **Autenticação por Sessão (`SessionAuthentication`) & Armazenamento Seguro:**
  - Evita o armazenamento de tokens sensíveis no `localStorage` do navegador;
  - O cookie de sessão (`sessionid`) é protegido nativamente com a diretiva `HttpOnly`, impedindo o acesso ou leitura direta da credencial via JavaScript;
  - A proteção integrada contra **CSRF** exige o envio do cabeçalho `X-CSRFToken` e `credentials: 'same-origin'` em todas as requisições de mutação (`POST`, `PATCH`, `DELETE`);
  - *Nota Técnica de Segurança:* Essa arquitetura reduz significativamente a superfície de ataque ao mitigar a exfiltração de credenciais via XSS e bloquear requisições forjadas entre sites (CSRF). Contudo, isso não representa uma proteção total contra todas as formas de XSS (como manipulação in-session no DOM), tornando essencial a manutenção de práticas de escape e sanitização de dados.
- **Frontend Vanilla (Sem Frameworks Pesados):** Desenvolvido com HTML5 semântico, CSS puro modularizado com **Design Tokens** (baseado na metodologia Atomic Design do Brad Frost) e JavaScript assíncrono nativo.
- **Transações Atômicas e Concorrência:** Criação de agendamentos protegida por `transaction.atomic()` e restrição única condicional no banco de dados (`UniqueConstraint`).

---

## 👥 Perfis de Usuários e Permissões

### 1. Cliente Comum (`is_staff = False`)
- Acesso à tela principal de agendamento (`/`).
- Consulta de catálogo de serviços ativos e horários livres em tempo real.
- Criação de novos agendamentos associados automaticamente à sua conta.
- Visualização exclusiva de seus próprios agendamentos (`/meus-agendamentos/`).
- Cancelamento de seus agendamentos que estejam nos status `pending` ou `confirmed`.
- Bloqueio total a painéis administrativos e rotas restritas (`403 Forbidden`).

### 2. Prestador de Serviços / Administrador (`is_staff = True`)
- Redirecionamento automático pós-login para o painel operacional (`/agenda/`).
- Visualização da agenda completa de atendimentos com filtros dinâmicos por data.
- Gestão de ciclo de vida do agendamento (Confirmar, Concluir, Cancelar).
- Acesso ao Django Admin (`/admin/`) para cadastro e edição de serviços.

---

## 📋 Regras de Negócio e Validações

1. **Horário de Funcionamento:**
   - Atendimentos ocorrem exclusivamente de **segunda a sexta-feira**.
   - Horários de início válidos: **09:00 às 17:00** (de hora em hora), garantindo encerramento do atendimento até às 18:00 com duração de 60 minutos.
2. **Prevenção de Horários no Passado:**
   - Bloqueio automático de agendamentos retroativos com base no fuso horário `America/Sao_Paulo`.
3. **Prevenção de Conflitos (*Anti-Overbooking*):**
   - Validação em camada tripla: no frontend (slots desabilitados), no serializer do DRF e no banco de dados via `UniqueConstraint`.
4. **Liberação por Cancelamento:**
   - Agendamentos com status `cancelled` liberam automaticamente o horário para que outros clientes possam agendar.
5. **Máquina de Estados de Status:**
   - `pending` (Pendente) ➔ `confirmed` (Confirmado) ou `cancelled` (Cancelado)
   - `confirmed` (Confirmado) ➔ `completed` (Concluído) ou `cancelled` (Cancelado)
   - `completed` (Concluído) ➔ *Estado terminal (não permite alteração)*
   - `cancelled` (Cancelado) ➔ *Estado terminal (não permite alteração)*

---

## 🛣️ Mapeamento de Rotas e Endpoints

### Rotas de Interface Web (HTML)

| Método | URL | Permissão | Descrição |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | `IsAuthenticated` | Tela de agendamento para cliente (redireciona staff para `/agenda/`). |
| `GET` | `/meus-agendamentos/` | `IsAuthenticated` | Histórico e cancelamento dos agendamentos do cliente. |
| `GET` | `/agenda/` | `IsAdminUser` (Staff) | Painel diário do prestador com gestão de status. |
| `GET`/`POST` | `/accounts/login/` | `AllowAny` | Formulário de login com proteção CSRF. |
| `POST` | `/accounts/logout/` | `IsAuthenticated` | Encerramento de sessão seguro via POST. |

### Endpoints da REST API (DRF)

| Método | Endpoint | Permissão | Descrição / Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/docs/` | `AllowAny` | Interface interativa do **Swagger UI** (OpenAPI 3.0). |
| `GET` | `/api/redoc/` | `AllowAny` | Documentação técnica visual via **Redoc**. |
| `GET` | `/api/schema/` | `AllowAny` | Especificação OpenAPI em formato YAML (`?format=json` para JSON). |
| `GET` | `/api/services/` | `IsAuthenticated` | Lista serviços ativos (ou todos para staff). |
| `GET` | `/api/available-slots/?date=YYYY-MM-DD` | `IsAuthenticated` | Retorna lista de horários livres das 09:00 às 17:00. |
| `GET` | `/api/appointments/` | `IsAuthenticated` | Lista agendamentos do cliente (ou todos para staff). |
| `POST` | `/api/appointments/` | `IsAuthenticated` | Cria agendamento: `{"service": 1, "date": "2026-09-01", "time": "14:00", "notes": "..."}` |
| `POST` | `/api/appointments/<id>/cancel/` | Dono ou Staff | Cancela agendamento e libera o horário no banco. |
| `PATCH` | `/api/appointments/<id>/status/` | `IsAdminUser` (Staff) | Atualiza status: `{"status": "confirmed" \| "completed" \| "cancelled"}` |
| `GET` | `/api/me/` | `IsAuthenticated` | Retorna dados cadastrais do usuário autenticado. |

---

## ⚙️ Instalação e Execução Local

### Pré-requisitos
- Python 3.10+ instalado.
- Git instalado.

### 1. Clonar o repositório e entrar no diretório
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

### 3. Configurar as variáveis de ambiente
Copie o arquivo `.env.example` para `.env`:
```bash
# Windows (PowerShell)
cp .env.example .env

# Linux / macOS
cp .env.example .env
```

### 4. Instalar as dependências
```bash
pip install -r requirements.txt
```

### 5. Executar as migrações do banco de dados
```bash
python manage.py migrate
```

### 6. Popular o banco com dados de demonstração (Seed Data)
Execute o comando customizado para carregar automaticamente o catálogo de serviços, usuários de teste e agendamentos:
```bash
python manage.py seed_data --reset
```

> 💡 **Dica:** Você também pode criar um superusuário manual caso prefira com `python manage.py createsuperuser`.

### 7. Iniciar o servidor de desenvolvimento
```bash
python manage.py runserver
```

Acesse a aplicação no navegador em: `http://127.0.0.1:8000/`  
Acesse a documentação interativa Swagger em: `http://127.0.0.1:8000/api/docs/`

---

### 🔑 Credenciais Pré-configuradas para Testes Rápidos

| Perfil | Usuário | Senha | Acesso / Painel |
| :--- | :--- | :--- | :--- |
| **Prestador / Staff (Admin)** | `admin` | `AdminPassword123!` | `/agenda/` e `/admin/` |
| **Cliente Padrão 1** | `cliente` | `ClientePassword123!` | `/` e `/meus-agendamentos/` |
| **Cliente Padrão 2** | `carlos` | `ClientePassword123!` | `/` e `/meus-agendamentos/` |

---

## 🧪 Suíte de Testes Automatizados

O projeto conta com **35 testes automatizados** cobrindo autenticação, documentação OpenAPI, integridade de banco de dados, máquina de estados, endpoints REST, comando de carga de dados e controle de acesso a páginas.

Para rodar todos os testes:
```bash
python manage.py test
```

### Cobertura dos Testes:
- **Autenticação Base e Documentação (`core` — 9 testes):**
  - Bloqueio anônimo em `/api/me/`, login com sucesso, login com senha inválida, retorno dos dados do usuário e revogação pós-logout.
  - Validação da especificação OpenAPI em `/api/schema/` (YAML e JSON).
  - Disponibilidade e integridade do Swagger UI (`/api/docs/`) e Redoc (`/api/redoc/`).
- **Domínio, Slots, Validações e Carga (`appointments` — 20 testes):**
  - Listagem de serviços ativos para cliente vs todos para staff.
  - Validação da duração padrão de 60 minutos.
  - Cálculo de slots disponíveis entre 09:00 e 17:00 (removendo slots ocupados).
  - Bloqueio de agendamentos aos finais de semana e no passado.
  - Bloqueio de início às 18:00 (expediente encerra às 18:00).
  - Prevenção de agendamentos duplicados com resposta `400 Bad Request`.
  - Isolamento de visibilidade por cliente logado.
  - Cancelamento pelo cliente e bloqueio de cancelamento por terceiros (`403 Forbidden`).
  - Transições de status válidas (`pending` ➔ `confirmed` ➔ `completed`) e rejeição de transições inválidas.
  - Execução e integridade do comando de gestão `python manage.py seed_data`.
- **Controle de Acesso a Páginas HTML (`appointments` — 6 testes):**
  - Redirecionamento de anônimos em `/`, `/meus-agendamentos/` e `/agenda/`.
  - Acesso de cliente comum a `/` carrega a tela de agendamento (`200 OK`).
  - Acesso de staff a `/` redireciona para `/agenda/` (`302 Found`).
  - Bloqueio no servidor para cliente comum tentando acessar `/agenda/` (`403 Forbidden`).
  - Acesso de staff a `/agenda/` carrega a agenda (`200 OK`).
  - Acesso a `/meus-agendamentos/` carrega com sucesso (`200 OK`).

---

## 📁 Estrutura do Projeto

```
projeto/
├── config/                     # Configurações do Django e rotas raiz
│   ├── asgi.py
│   ├── settings.py             # Configurações com Decouple (.env), SessionAuth, CSRF
│   ├── urls.py                 # Roteamento central e documentação OpenAPI
│   └── wsgi.py
├── core/                       # App base de autenticação e utilitários
│   ├── apps.py
│   ├── tests.py                # Testes de autenticação, sessão e OpenAPI
│   ├── urls.py
│   └── views.py                # Endpoint /api/me/
├── appointments/               # App de domínio (Agendamentos e Serviços)
│   ├── admin.py                # Registro no Django Admin
│   ├── apps.py
│   ├── management/             # Comandos customizados do Django
│   │   └── commands/
│   │       └── seed_data.py    # Comando para carga inicial de demonstração
│   ├── migrations/             # Migrações do banco de dados
│   ├── models.py               # Modelos Service e Appointment + Constraints
│   ├── serializers.py          # Serializers do DRF com regras de negócio
│   ├── tests.py                # Testes de API, regras, páginas e seed
│   ├── urls.py                 # Rotas HTML e da API
│   └── views.py                # TemplateViews e APIViews
├── static/                     # Arquivos estáticos
│   ├── css/
│   │   └── style.css           # Design Tokens, Atomic Design e Responsividade
│   └── js/
│       ├── booking.js          # Lógica de agendamento interativo
│       ├── csrf.js             # Utilitário de CSRF e fetch seguro
│       ├── my_appointments.js  # Visualização e cancelamento de agendamentos
│       └── staff_agenda.js     # Painel do prestador com filtros e status
├── templates/                  # Templates Django
│   ├── base.html               # Shell da aplicação, navbar e token CSRF
│   ├── registration/
│   │   └── login.html          # Tela de login estilizada
│   └── appointments/
│       ├── book.html           # Tela de agendamento por etapas
│       ├── my_appointments.html# Tela "Meus Agendamentos"
│       └── staff_agenda.html   # Painel diário da agenda
├── .env.example                # Modelo de variáveis de ambiente
├── manage.py
├── requirements.txt            # Dependências com python-decouple
├── .gitignore                  # Arquivos e pastas ignoradas no versionamento
└── README.md                   # Documentação completa do projeto
```

---

## 📄 Licença

Projeto desenvolvido para fins de estudo e portfólio. Livre para uso e adaptação.

