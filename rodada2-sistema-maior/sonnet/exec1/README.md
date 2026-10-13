# Clínica API

API REST para gestão de uma clínica médica de médio porte, construída com FastAPI, SQLAlchemy (SQLite) e autenticação JWT.

## Arquitetura

Código organizado em camadas, com dependência de cima para baixo:

```
app/
├── routers/      # Camada HTTP: rotas FastAPI, validação de entrada, controle de acesso por perfil
├── services/      # Regras de negócio (agendamento, faturamento, prontuário, auditoria, etc.)
├── repositories/  # Acesso a dados via SQLAlchemy
├── models/        # Entidades ORM (SQLAlchemy)
├── schemas/       # Contratos de entrada/saída (Pydantic)
├── core/          # Segurança, autenticação, exceções e permissões transversais
├── utils/         # Validadores (CPF, CRM) e paginação
├── config.py      # Configuração via variáveis de ambiente
├── database.py    # Engine/Session SQLAlchemy
└── main.py        # Montagem da aplicação e tratamento centralizado de erros
```

## Perfis e permissões

`administrador`, `medico`, `enfermeiro`, `recepcionista`, `paciente` — cada endpoint valida o perfil via dependências FastAPI (`app/core/deps.py`, `app/core/permissions.py`).

## Como rodar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # ajuste SECRET_KEY em produção

uvicorn app.main:app --reload
```

A documentação interativa fica em `http://localhost:8000/docs`.

## Testes

```bash
source .venv/bin/activate
pytest
```

Os testes usam SQLite em memória (isolado por teste) e cobrem os principais fluxos de negócio: autenticação/bloqueio de conta, CRUD e controle de acesso de pacientes/profissionais, conflitos e regras de agendamento, prontuário/prescrições/exames, faturamento (desconto de convênio, prevenção de pagamento duplicado) e relatórios.

## Observações de segurança

- Senhas com hash bcrypt (`passlib`) e política de senha forte.
- Access token de curta duração (15 min) + refresh token (7 dias) revogável, ambos JWT.
- Bloqueio de conta por 15 minutos após 5 tentativas de login malsucedidas.
- Log de auditoria (`AuditLog`) registrado para toda ação sensível (login, troca de senha, criação/alteração de pacientes, prontuários, faturamento, etc.).
- Recuperação de senha via token opaco de uso único com expiração — em produção, o token seria enviado por e-mail em vez de retornado na resposta da API.
