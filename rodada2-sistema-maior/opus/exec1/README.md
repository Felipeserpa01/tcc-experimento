# API de Gestao de Clinica Medica

API REST **production-ready** para a gestao de uma clinica medica de medio porte, construida
com **Python + FastAPI + SQLAlchemy (SQLite) + JWT + pytest**, organizada em camadas com
separacao clara de responsabilidades.

---

## Sumario

- [Arquitetura](#arquitetura)
- [Como executar](#como-executar)
- [Configuracao](#configuracao)
- [Perfis e permissoes](#perfis-e-permissoes)
- [Modulos e regras de negocio](#modulos-e-regras-de-negocio)
- [Endpoints](#endpoints)
- [Padrao de erros](#padrao-de-erros)
- [Paginacao, filtros e ordenacao](#paginacao-filtros-e-ordenacao)
- [Testes](#testes)
- [Decisoes de projeto](#decisoes-de-projeto)

---

## Arquitetura

O projeto segue uma arquitetura em camadas. Cada camada so conhece a camada imediatamente
abaixo dela:

```
HTTP  ->  app/api/         Rotas: validacao de entrada/saida e injecao de dependencias
      ->  app/services/    Regras de negocio, autorizacao de dominio e transacoes
      ->  app/repositories Consultas ao banco (SQLAlchemy), sem regra de negocio
      ->  app/models/      Modelos ORM e invariantes do dominio
```

```
app/
├── api/
│   ├── dependencies.py        # usuario atual, require_roles(...)
│   ├── router.py              # agregador da API v1
│   └── v1/                    # auth, users, patients, professionals, appointments,
│                              # medical_records, billing, reports, audit
├── core/
│   ├── config.py              # configuracao 100% por variaveis de ambiente
│   ├── context.py             # contexto da requisicao (IP, user-agent, request id)
│   ├── datetime_utils.py      # convencao de data/hora do projeto
│   ├── error_handlers.py      # tratamento centralizado de erros
│   ├── exceptions.py          # hierarquia de erros de dominio
│   ├── middleware.py          # X-Request-ID e log de acesso
│   ├── pagination.py          # Page[T], PaginationParams e ordenacao validada
│   └── security.py            # hash de senha, politica de senha, JWT
├── db/                        # engine, sessao, base declarativa, bootstrap
├── models/                    # User, Patient, Professional, Appointment, MedicalRecord,
│                              # Prescription, ExamRequest, Charge, AuditLog, ...
├── repositories/              # acesso a dados por agregado
├── schemas/                   # contratos Pydantic de entrada e saida
├── services/                  # regras de negocio
└── utils/validators.py        # CPF, CRM/COREN, telefone, CEP, UF
```

### Entidades principais

| Entidade | Descricao |
|---|---|
| `User` | Credencial de acesso, perfil, bloqueio por tentativas |
| `RefreshToken` / `PasswordResetToken` | Sessoes revogaveis e recuperacao de senha |
| `Patient` / `HealthInsurance` | Cadastro do paciente e convenio com percentual de desconto |
| `Professional` / `ProfessionalSchedule` | Medico ou enfermeiro e sua agenda semanal |
| `Appointment` / `WaitlistEntry` | Consulta e lista de espera |
| `MedicalRecord` / `Prescription` / `ExamRequest` / `ExamAttachment` | Prontuario, prescricoes, exames e anexos |
| `Charge` | Cobranca com desconto de convenio e pagamento |
| `AuditLog` / `Notification` | Auditoria de acoes sensiveis e notificacoes internas |

---

## Como executar

```bash
# 1. Ambiente virtual e dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configuracao
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"   # cole em SECRET_KEY

# 3. Subir a API (cria o schema e o admin inicial no boot)
uvicorn app.main:app --reload
```

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- Health check: <http://localhost:8000/health>

O administrador inicial e criado no boot a partir de `FIRST_ADMIN_EMAIL` e
`FIRST_ADMIN_PASSWORD` (se informados e se ainda nao existir).

### Fluxo rapido

```bash
BASE=http://localhost:8000/api/v1

# login
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@clinica.com.br","password":"Admin@123456"}' | jq -r .access_token)

# cadastrar um medico com agenda
curl -X POST $BASE/professionals -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{
    "full_name":"Carlos Souza","professional_type":"doctor",
    "council_number":"123456","council_state":"SP","specialty":"Cardiologia",
    "appointment_price":"300.00",
    "schedules":[{"weekday":0,"start_time":"08:00:00","end_time":"18:00:00"}]
  }'
```

---

## Configuracao

Nenhum segredo esta no codigo: tudo vem de variaveis de ambiente (veja `.env.example`).

| Variavel | Padrao | Descricao |
|---|---|---|
| `ENVIRONMENT` | `development` | `development`, `testing` ou `production` |
| `SECRET_KEY` | *(vazio)* | **Obrigatoria em producao**. Fora de producao e gerada em memoria |
| `DATABASE_URL` | `sqlite:///./clinica.db` | URL do banco |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Validade do access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Validade do refresh token |
| `MAX_LOGIN_ATTEMPTS` | `5` | Tentativas antes do bloqueio |
| `ACCOUNT_LOCKOUT_MINUTES` | `15` | Duracao do bloqueio |
| `PASSWORD_MIN_LENGTH` | `8` | Minimo da politica de senha |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `20` / `100` | Paginacao |
| `UPLOAD_DIR` / `MAX_UPLOAD_SIZE_MB` | `uploads` / `10` | Anexos de exames |
| `ALLOWED_UPLOAD_EXTENSIONS` | `.pdf,.png,...` | Extensoes aceitas |
| `TIMEZONE` | `America/Sao_Paulo` | Fuso usado em toda a agenda |

A aplicacao **recusa iniciar** em producao sem `SECRET_KEY` ou com `DEBUG=true`.

---

## Perfis e permissoes

| Recurso | admin | doctor | nurse | receptionist | patient |
|---|:--:|:--:|:--:|:--:|:--:|
| Usuarios (CRUD) | ✅ | – | – | – | – |
| Log de auditoria | ✅ | – | – | – | – |
| Convenios | ✅ | leitura | leitura | ✅ | leitura |
| Pacientes (criar/editar) | ✅ | – | – | ✅ | proprio contato |
| Pacientes (ler) | todos | todos | todos | todos | **somente o proprio** |
| Excluir paciente | ✅ | – | – | – | – |
| Profissionais (CRUD) | ✅ | proprio cadastro | proprio cadastro | leitura | leitura |
| Agenda de disponibilidade | ✅ | propria | propria | leitura | leitura |
| Agendar consulta | ✅ | – | ✅ | ✅ | **para si** |
| Confirmar / cancelar / remarcar | ✅ | propria agenda | ✅ | ✅ | proprias |
| Iniciar / concluir atendimento | – | **medico responsavel** | – | – | – |
| Registrar falta | ✅ | propria agenda | ✅ | ✅ | – |
| Prontuario / prescricao / exame (escrita) | – | **medico responsavel** | – | – | – |
| Prontuario / prescricao / exame (leitura) | ✅ | ✅ | ✅ | ✅ | **somente o proprio** |
| Faturamento | ✅ | – | – | ✅ | le as proprias cobrancas |
| Relatorios clinicos | ✅ | **apenas os proprios dados** | ✅ | ✅ | – |
| Relatorios financeiros | ✅ | – | – | ✅ | – |

O controle acontece em dois niveis: `require_roles(...)` nas rotas (perfil) e verificacao de
propriedade do recurso na camada de servico (ex.: "este prontuario e deste paciente?").

---

## Modulos e regras de negocio

### 1. Autenticacao e seguranca
- Access token JWT de curta duracao + refresh token persistido e **revogavel**.
- **Rotacao de refresh token**: ao renovar, o token anterior e revogado. O reuso de um token
  ja revogado e tratado como indicio de roubo e **encerra todas as sessoes** do usuario.
- Senhas com **bcrypt** (salt por senha) e politica forte: minimo 8 caracteres, letra, numero
  e simbolo, alem de bloqueio de senhas obvias.
- **Bloqueio temporario** apos 5 tentativas malsucedidas (configuravel). O contador zera no
  primeiro login bem-sucedido; o admin pode destravar via `POST /users/{id}/unlock`.
- Troca de senha e recuperacao por token de uso unico com validade curta. A resposta da
  recuperacao e **sempre neutra**, para nao revelar quais emails existem.
- **Auditoria** de acoes sensiveis com quem (usuario, perfil, IP, user-agent), o que (acao,
  recurso, id) e quando, incluindo tentativas que falharam.

### 2. Pacientes
- CRUD completo com endereco estruturado, convenio, alergias e observacoes.
- **CPF validado pelos dois digitos verificadores** e armazenado apenas com digitos.
- Busca por nome, CPF, convenio ou cidade, com paginacao e ordenacao.
- Exclusao e **logica** (`is_active = false`), preservando o historico clinico.

### 3. Profissionais
- CRUD de medicos e enfermeiros; o conselho (`CRM` para medico, `COREN` para enfermeiro) e
  derivado do tipo e validado em numero (4-7 digitos) e UF.
- Especialidade obrigatoria para medicos; busca por especialidade.
- Agenda semanal de disponibilidade por dia da semana e faixa de horario, com bloqueio de
  faixas sobrepostas.
- `GET /professionals/{id}/available-slots?date=` gera a grade de horarios livres.

### 4. Agendamento
Ao agendar ou remarcar, a API valida em sequencia:
1. o horario nao pode estar no passado;
2. paciente e profissional precisam estar ativos e o profissional precisa ser medico;
3. o intervalo precisa estar **integralmente dentro** de uma faixa ativa da agenda;
4. o medico nao pode ter outra consulta sobreposta;
5. o paciente nao pode ter outra consulta sobreposta.

Ciclo de vida com transicoes explicitas:

```
scheduled ──► confirmed ──► in_progress ──► completed
    │             │              │
    ├─────────────┴──────────────┴──► cancelled
    └─────────────┴──► no_show
```

- Cancelamento exige motivo e registra quem cancelou.
- **Lista de espera**: quando um horario vaga (cancelamento ou remarcacao), os pacientes da
  fila daquele medico e daquela data sao notificados automaticamente (respeitando a faixa de
  horario preferida). Quando o paciente consegue agendar, sua entrada vira `fulfilled`.
- `GET /professionals/{id}/agenda?date=` devolve a agenda do dia.

### 5. Prontuario, prescricoes e exames
- Prontuario 1:1 com a consulta, permitido apenas em consultas **iniciadas ou realizadas**.
- **Somente o medico responsavel pela consulta** registra e edita prontuario, prescricoes e
  exames — nem outro medico, nem enfermeiro, nem admin.
- O paciente **le** o proprio prontuario, prescricoes e exames, mas nunca escreve.
- Exames aceitam resultado textual e anexos de arquivo, com validacao de extensao, tamanho e
  **sanitizacao do nome do arquivo** (impede path traversal).
- `GET /patients/{id}/history` devolve o historico clinico completo em ordem cronologica.

### 6. Faturamento
- Cobranca de consulta, exame ou servico avulso; o valor padrao vem do profissional/exame.
- O **desconto do convenio** do paciente e aplicado automaticamente
  (`net = gross - gross * desconto%`), com arredondamento monetario de 2 casas.
- Uma consulta/exame nao pode ter duas cobrancas ativas ao mesmo tempo.
- **Impossivel pagar duas vezes**: pagar uma cobranca ja quitada retorna `409` (e a tentativa
  fica registrada na auditoria). Cobranca cancelada tambem nao pode ser paga, e cobranca paga
  nao pode ser cancelada.

### 7. Relatorios
| Endpoint | Conteudo |
|---|---|
| `GET /reports/appointments` | Total por periodo, por status (com %), por medico e por especialidade |
| `GET /reports/revenue` | Faturado, recebido, pendente, cancelado, descontos, por forma de pagamento e por status |
| `GET /reports/no-show` | Taxa de faltas por medico e taxa geral |
| `GET /reports/top-patients` | Pacientes mais atendidos |

Todas as agregacoes sao feitas em SQL (`GROUP BY`), nao em memoria.

---

## Endpoints

Prefixo: `/api/v1`.

<details>
<summary><b>Autenticacao</b></summary>

| Metodo | Rota | Descricao |
|---|---|---|
| POST | `/auth/register` | Auto cadastro de paciente |
| POST | `/auth/login` | Login (JSON) |
| POST | `/auth/token` | Login OAuth2 (usado pelo Swagger) |
| POST | `/auth/refresh` | Renova o access token com rotacao |
| POST | `/auth/logout` | Encerra uma ou todas as sessoes |
| GET | `/auth/me` | Dados do usuario autenticado |
| POST | `/auth/change-password` | Troca de senha |
| POST | `/auth/password-recovery` | Solicita token de recuperacao |
| POST | `/auth/password-reset` | Redefine a senha com o token |
</details>

<details>
<summary><b>Usuarios, pacientes e convenios</b></summary>

| Metodo | Rota |
|---|---|
| POST/GET | `/users`, `/users/{id}` |
| POST | `/users/{id}/activate`, `/deactivate`, `/unlock`, `/reset-password` |
| POST/GET/PATCH | `/insurances`, `/insurances/{id}` |
| POST/GET | `/patients`, `/patients/me`, `/patients/{id}` |
| PATCH/DELETE | `/patients/{id}` |
| GET | `/patients/{id}/history` |
</details>

<details>
<summary><b>Profissionais e agenda</b></summary>

| Metodo | Rota |
|---|---|
| POST/GET/PATCH/DELETE | `/professionals`, `/professionals/{id}` |
| GET | `/professionals/me`, `/professionals/specialties` |
| POST/GET/PATCH/DELETE | `/professionals/{id}/schedules[/{schedule_id}]` |
| GET | `/professionals/{id}/available-slots?date=` |
| GET | `/professionals/{id}/agenda?date=` |
</details>

<details>
<summary><b>Consultas, prontuario e exames</b></summary>

| Metodo | Rota |
|---|---|
| POST/GET/PATCH | `/appointments`, `/appointments/{id}` |
| POST | `/appointments/{id}/confirm`, `/cancel`, `/reschedule`, `/start`, `/complete`, `/no-show` |
| POST/GET/DELETE | `/waitlist`, `/waitlist/{id}` |
| POST/GET | `/appointments/{id}/medical-record`, `/prescriptions`, `/exams` |
| GET/PATCH | `/medical-records`, `/medical-records/{id}` |
| PATCH/DELETE | `/prescriptions/{id}` |
| GET/PATCH/POST | `/exams/{id}`, `/exams/{id}/status`, `/exams/{id}/result` |
| POST/GET | `/exams/{id}/attachments` |
| GET | `/exams/attachments/{id}/download` |
</details>

<details>
<summary><b>Faturamento, relatorios e auditoria</b></summary>

| Metodo | Rota |
|---|---|
| POST/GET | `/charges`, `/charges/{id}` |
| POST | `/charges/{id}/pay`, `/charges/{id}/cancel` |
| GET | `/reports/appointments`, `/reports/revenue`, `/reports/no-show`, `/reports/top-patients` |
| GET | `/audit-logs` |
| GET/POST | `/notifications`, `/notifications/{id}/read`, `/notifications/read-all` |
</details>

---

## Padrao de erros

Toda falha retorna o mesmo envelope, produzido pelos handlers centrais em
`app/core/error_handlers.py`:

```json
{
  "error": {
    "code": "schedule_conflict",
    "message": "O profissional ja possui uma consulta neste horario.",
    "details": {
      "conflicting_appointment_id": 12,
      "conflicting_window": "2026-03-02T09:00:00 -> 2026-03-02T09:30:00"
    },
    "request_id": "6b1f0a2c9e2a4f1b8f0f2c3d4e5f6a7b"
  }
}
```

| Codigo HTTP | Quando acontece |
|---|---|
| `400` | Parametro invalido (ex.: campo de ordenacao desconhecido) |
| `401` | Token ausente, invalido, expirado ou credenciais erradas |
| `403` | Perfil sem permissao ou conta desativada |
| `404` | Recurso inexistente |
| `409` | Conflito de estado: CPF/email duplicado, horario ocupado, cobranca ja paga |
| `413` / `415` | Anexo grande demais / extensao nao permitida |
| `422` | Validacao de dados ou violacao de regra de negocio |
| `500` | Erro inesperado (detalhes so aparecem com `DEBUG=true`) |

Erros de validacao listam cada campo:

```json
{"error": {"code": "validation_error", "message": "...", "details": [
  {"field": "cpf", "location": "body", "message": "CPF invalido...", "type": "value_error"}
]}}
```

---

## Paginacao, filtros e ordenacao

Todas as listagens aceitam `page`, `size`, `sort_by` e `sort_order`, e devolvem o mesmo
envelope:

```json
{
  "items": [],
  "meta": {"total": 57, "page": 2, "size": 20, "pages": 3,
           "has_next": true, "has_previous": true}
}
```

`sort_by` e validado contra uma **lista branca** de colunas por recurso; um campo desconhecido
retorna `400` informando as opcoes validas (evita ordenacao por colunas sensiveis).

---

## Testes

```bash
pytest                              # suite completa
pytest --cov=app --cov-report=term-missing
pytest tests/test_appointments.py -v
```

Cada teste roda contra um banco SQLite em memoria proprio (isolamento total) e a maior parte
exercita a API de ponta a ponta via `TestClient`.

| Arquivo | Cobertura |
|---|---|
| `test_validators.py` | CPF (digitos verificadores), CRM/COREN, telefone, CEP, UF, politica de senha, hash |
| `test_auth.py` | Registro, login, bloqueio apos 5 tentativas, rotacao/reuso de refresh token, logout, troca e recuperacao de senha, auditoria |
| `test_patients.py` | CRUD, duplicidade de CPF, busca, paginacao, ordenacao e escopo do paciente |
| `test_professionals.py` | CRUD, validacao de conselho, agenda sobreposta, slots livres |
| `test_appointments.py` | Conflitos, disponibilidade, passado, transicoes de status, remarcacao, faltas, lista de espera |
| `test_medical_records.py` | Restricao ao medico responsavel, prescricoes, exames, anexos, historico clinico |
| `test_billing.py` | Desconto de convenio, pagamento, pagamento duplicado, cancelamento |
| `test_reports.py` | Agregacoes dos quatro relatorios e escopo por perfil |
| `test_users_and_errors.py` | Gestao de usuarios, envelope de erro, notificacoes, health |

---

## Decisoes de projeto

- **Data/hora sem timezone, no fuso da clinica.** Misturar `datetime` com e sem timezone e a
  origem mais comum de bugs em agenda. Todo o sistema usa horario local naive
  (`app/core/datetime_utils.py`); entradas com timezone sao convertidas na borda.
- **Excecoes de dominio, nao `HTTPException`.** Os servicos levantam erros de negocio
  (`ScheduleConflictError`, `BusinessRuleError`, ...) e um handler central traduz para HTTP.
  A regra de negocio nao conhece o protocolo.
- **Autorizacao em duas camadas.** Perfil na rota, propriedade do recurso no servico. Assim um
  `doctor` valido ainda e barrado ao tocar a consulta de um colega.
- **Exclusao logica** para pacientes e profissionais: prontuario e faturamento sao registros
  legais e nao podem desaparecer.
- **Refresh token persistido.** JWT puro nao permite revogar sessao; guardar o hash do token
  habilita logout real, rotacao e deteccao de reuso.
- **`Numeric(10,2)` e `Decimal`** em todo valor monetario, nunca `float`.
- **Chaves estrangeiras habilitadas no SQLite** (`PRAGMA foreign_keys=ON`), que por padrao vem
  desligadas e deixariam passar referencias orfas.
