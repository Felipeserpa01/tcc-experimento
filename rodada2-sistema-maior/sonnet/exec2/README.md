# Clinic Management API

API REST para gestão de uma clínica médica de médio porte, construída com FastAPI, SQLAlchemy (SQLite) e autenticação JWT.

## Stack

- **Linguagem:** Python 3.12+
- **Framework:** FastAPI
- **Banco de dados:** SQLite (via SQLAlchemy ORM)
- **Autenticação:** JWT (access + refresh tokens)
- **Testes:** pytest + httpx (TestClient)

## Arquitetura

O código é organizado em camadas, com responsabilidades bem separadas:

```
app/
├── main.py              # Ponto de entrada da aplicação FastAPI
├── config.py             # Configuração via variáveis de ambiente (pydantic-settings)
├── database.py            # Engine, sessão e Base declarativa do SQLAlchemy
├── dependencies.py         # Dependências compartilhadas (usuário atual, RBAC)
├── core/
│   ├── enums.py           # Enums de domínio (papéis, status, etc.)
│   ├── exceptions.py        # Exceções de domínio e handlers centralizados
│   ├── security.py         # Hash de senha, JWT, tokens de reset
│   └── validators.py        # Validadores de CPF, CRM e força de senha
├── models/               # Modelos ORM (SQLAlchemy)
├── schemas/               # Schemas Pydantic (entrada/saída)
├── repositories/            # Acesso a dados (queries)
├── services/               # Regras de negócio e orquestração
└── routes/                # Endpoints FastAPI (camada HTTP)
```

## Módulos implementados

1. **Autenticação e segurança** — registro/login JWT, 5 perfis de acesso, RBAC granular, política de senha forte, bloqueio de conta após 5 tentativas malsucedidas, troca/recuperação de senha, log de auditoria.
2. **Gestão de pacientes** — CRUD completo, validação de CPF, busca com paginação/ordenação, controle de acesso (paciente só vê os próprios dados).
3. **Gestão de profissionais** — CRUD de médicos/enfermeiros, validação de CRM, agenda de disponibilidade semanal, busca por especialidade.
4. **Agendamento de consultas** — conflito de horário, validação contra a agenda do profissional, confirmação/cancelamento/remarcação, lista de espera com notificação automática, agenda diária.
5. **Atendimento, prontuário e prescrições** — prontuário, prescrições e exames restritos ao médico responsável pela consulta; histórico clínico cronológico do paciente.
6. **Faturamento** — cobrança de consultas/exames, desconto de convênio configurável, controle de status (pendente/pago/cancelado), bloqueio de pagamento duplicado.
7. **Relatórios** — consultas por período/médico/especialidade/status, faturamento por período/forma de pagamento, taxa de no-show por médico, pacientes mais atendidos.

## Perfis de acesso

| Perfil | Descrição |
|---|---|
| `administrador` | Acesso total ao sistema |
| `medico` | Atendimento, prontuário, prescrições, exames, própria agenda |
| `enfermeiro` | Apoio ao atendimento, própria agenda |
| `recepcionista` | Cadastro de pacientes, agendamento, faturamento |
| `paciente` | Acesso apenas aos próprios dados, consultas e histórico clínico |

## Como executar

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edite .env e defina JWT_SECRET_KEY, INITIAL_ADMIN_EMAIL e INITIAL_ADMIN_PASSWORD

uvicorn app.main:app --reload
```

A documentação interativa fica disponível em `http://localhost:8000/docs`.

### Bootstrap do primeiro administrador

Como o autorregistro público (`POST /auth/register`) só permite o perfil `paciente`, e apenas um administrador pode criar contas de equipe, a aplicação cria automaticamente uma conta `administrador` na inicialização se as variáveis `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD` estiverem definidas e nenhum usuário com aquele e-mail já existir.

### Fluxo de cadastro de usuários

- **Paciente:** se autorregistra em `POST /auth/register` (cria login) e, em seguida, um administrador/recepcionista cria o cadastro clínico em `POST /patients`, opcionalmente vinculando-o à conta via `user_id`.
- **Médico/Enfermeiro:** criado por um administrador em `POST /professionals` (cria login + perfil profissional em uma única operação).
- **Recepcionista/Administrador:** criado por um administrador em `POST /users`.

## Rodando os testes

```bash
pytest
pytest --cov=app --cov-report=term-missing   # com cobertura
```

A suíte cobre os principais fluxos de cada módulo, regras de negócio (conflito de agenda, bloqueio de conta, desconto de convênio, transições de status de consulta, etc.) e casos de borda (CPF/CRM inválidos, tentativas de acesso não autorizado, pagamento duplicado, entre outros).

## Notas de produção

- Os segredos (chave JWT, credenciais do admin inicial) são lidos exclusivamente de variáveis de ambiente — nada fica hardcoded no código.
- O tratamento de erros é centralizado (`app/core/exceptions.py`), retornando códigos HTTP apropriados (400/401/403/404/409/422/423) com mensagens claras.
- O SQLite é adequado para o escopo deste projeto; em um cenário de produção com maior concorrência, a troca do `DATABASE_URL` para Postgres é suportada pela mesma camada de acesso a dados (SQLAlchemy), sem alterações de código.
- O token de recuperação de senha nunca é retornado pela API — em produção, seria enviado por e-mail. O fluxo é testado diretamente via `AuthService` nos testes de integração.
