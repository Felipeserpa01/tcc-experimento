# Clínica Médica API

API REST para gestão de uma clínica médica de médio porte, construída com **FastAPI**, **SQLAlchemy 2 (SQLite)**,
**JWT** e **pytest**.

Módulos: autenticação e segurança · pacientes · profissionais e agenda · agendamento com lista de espera ·
prontuário, prescrições e exames · faturamento · relatórios e indicadores.

---

## Sumário

1. [Como executar](#como-executar)
2. [Arquitetura](#arquitetura)
3. [Perfis e permissões](#perfis-e-permissões)
4. [Regras de negócio](#regras-de-negócio)
5. [Endpoints](#endpoints)
6. [Erros e validação](#erros-e-validação)
7. [Testes](#testes)
8. [Decisões de projeto e limitações](#decisões-de-projeto-e-limitações)

---

## Como executar

Requisitos: Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env
# defina SECRET_KEY (obrigatória, mín. 32 caracteres):
python -c "import secrets; print(secrets.token_urlsafe(48))"

# (opcional) crie o primeiro administrador pela linha de comando
python -m app.cli create-admin --email admin@clinica.com.br --name "Ana Administradora"

uvicorn app.main:app --reload
```

- Documentação interativa: <http://localhost:8000/docs> (Swagger) e <http://localhost:8000/redoc>
- Todas as rotas de negócio ficam sob o prefixo `/api/v1`.
- Alternativa ao CLI: definir `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD`; o administrador é criado na
  inicialização se ainda não existir nenhum.

### Configuração

Toda a configuração vem de variáveis de ambiente (ou `.env`). Não há segredos no código: sem `SECRET_KEY`, a
aplicação não inicia; valores fracos (ex.: `changeme`) são rejeitados. Veja `.env.example` para a lista completa
(expiração dos tokens, política de bloqueio, fuso horário, limite de upload, SMTP etc.).

---

## Arquitetura

```
app/
├── main.py              # criação da aplicação, middlewares, lifespan
├── cli.py               # comandos administrativos (init-db, create-admin)
├── api/                 # camada HTTP
│   ├── deps.py          #   autenticação, permissões, paginação, injeção de serviços
│   ├── presenters.py    #   montagem de respostas compostas
│   └── routes/          #   um router por módulo
├── services/            # regras de negócio (casos de uso)
│   ├── scheduling.py    #   regras puras de agenda e transições de status
│   └── access.py        #   regras de escopo (dono do dado, médico responsável)
├── repositories/        # acesso a dados (SQLAlchemy)
├── models/              # entidades ORM, enums e tipos de coluna
├── schemas/             # contratos de entrada/saída (Pydantic)
├── core/                # config, segurança, banco, erros, permissões, middleware, relógio
└── utils/               # validadores (CPF, CRM, telefone...) e cálculo monetário
```

Fluxo de uma requisição: **rota** (valida entrada e permissão do perfil) → **serviço** (regras de negócio, escopo,
auditoria, transação) → **repositório** (consultas) → **modelo**. Os serviços lançam exceções de domínio que o
tratador central converte em respostas HTTP.

Entidades: usuário, refresh token, token de recuperação de senha, convênio, paciente, profissional,
disponibilidade, consulta, lista de espera, prontuário, prescrição, exame, cobrança, notificação e log de auditoria.

---

## Perfis e permissões

O controle é feito por **permissões** atribuídas a cada perfil (`app/core/permissions.py`), complementadas por
**regras de escopo** nos serviços.

| Recurso / ação                               | Admin | Recepção | Médico          | Enfermeiro   | Paciente               |
|----------------------------------------------|:-----:|:--------:|:---------------:|:------------:|:----------------------:|
| Usuários, auditoria, relatórios              | ✔     |          |                 |              |                        |
| Convênios (gerenciar / consultar)            | ✔ / ✔ | – / ✔    | – / ✔           | – / ✔        | – / ✔                  |
| Cadastrar paciente                           | ✔     | ✔        |                 |              | autocadastro           |
| Consultar pacientes                          | ✔     | ✔        | ✔               | ✔            | só a própria ficha     |
| Atualizar paciente                           | todos os campos | todos os campos | alergias/observações | alergias/observações | contato próprio |
| Desativar paciente                           | ✔     |          |                 |              |                        |
| Cadastrar/editar profissionais               | ✔     |          |                 |              |                        |
| Agenda de disponibilidade                    | ✔     | ✔        | só a própria    | só a própria |                        |
| Agendar consulta                             | ✔     | ✔        |                 |              | só para si             |
| Confirmar / cancelar / remarcar              | ✔     | ✔        | próprias consultas |           | próprias consultas     |
| Iniciar / finalizar atendimento              |       |          | médico responsável |           |                        |
| Registrar falta                              | ✔     | ✔        | médico responsável |           |                        |
| Prontuário, prescrições, exames (escrita)    |       |          | médico responsável |           |                        |
| Prontuário, prescrições, exames (leitura)    |       |          | ✔               | ✔            | somente os próprios    |
| Faturamento (gerenciar / consultar)          | ✔ / ✔ | ✔ / ✔    |                 |              | – / próprias cobranças |

Dados clínicos não são expostos a administradores e recepcionistas (princípio do menor privilégio / LGPD).

---

## Regras de negócio

### Autenticação e segurança
- **JWT**: access token curto (15 min por padrão) + refresh token (7 dias) com **rotação**. Reapresentar um refresh
  token já rotacionado revoga todas as sessões do usuário (detecção de roubo de token).
- Senhas com **bcrypt**; política: mínimo 8 caracteres, com letra, número e símbolo (máx. 72 bytes, limite do bcrypt).
- **Bloqueio temporário** após 5 tentativas malsucedidas consecutivas (15 min, configurável) → HTTP 423. O
  administrador pode desbloquear manualmente.
- Login com e-mail inexistente e com senha errada retornam a mesma mensagem, e o tempo de resposta é equalizado.
- **Troca de senha** e **redefinição** incrementam a versão de token do usuário: todos os tokens emitidos antes
  deixam de valer. A desativação da conta tem o mesmo efeito.
- **Recuperação de senha**: código aleatório de uso único, armazenado apenas como hash SHA-256, válido por 30 min,
  enviado por e-mail. A resposta é sempre a mesma, exista o e-mail ou não.
- **Auditoria**: login (sucesso/falha/bloqueio), senhas, usuários, pacientes, profissionais, agenda, consultas,
  prontuário (inclusive **visualização**), prescrições, exames e cobranças. Cada registro guarda usuário, perfil,
  ação, entidade, detalhes, IP, ID da requisição e data/hora. Senhas e tokens nunca são registrados.

### Pacientes
- CPF validado pelos dígitos verificadores, armazenado só com dígitos e único.
- Telefone brasileiro (fixo/celular com DDD), CEP, UF, nome e data de nascimento validados.
- Busca por nome, CPF (prefixo), convênio (ID ou nome), com paginação e ordenação.
- A exclusão é **lógica**: o histórico clínico e financeiro é preservado. Não é possível desativar um paciente com
  consultas futuras ativas.

### Profissionais e agenda
- Médicos exigem **CRM** (validado e normalizado para `CRM/UF NNNNNN`) e especialidade. Enfermeiros exigem **COREN**.
- Faixas semanais de disponibilidade (dia, início, fim, duração da consulta), sem sobreposição no mesmo dia.
- `GET /professionals/{id}/available-slots?date=` lista os horários livres do dia.

### Agendamento
- Apenas médicos ativos. O horário deve estar **dentro da disponibilidade**, alinhado aos intervalos da faixa, no
  **futuro** e em até 365 dias.
- **Sem conflito**: nem o médico nem o paciente podem ter consultas ativas sobrepostas. Além da verificação na
  aplicação, um **índice único parcial** no banco impede duas consultas ativas do mesmo médico no mesmo horário
  (proteção contra condições de corrida).
- Status e transições permitidas:

  ```
  agendada ──► confirmada ──► em_andamento ──► realizada
     │  │           │  │
     │  └──► cancelada ◄┘  (com motivo; somente antes do horário)
     └────► faltou ◄───┘   (somente após o horário)
  ```
- Remarcar volta a consulta para `agendada` (exige nova confirmação) e libera o horário anterior.
- Atendimento só pode ser iniciado no dia da consulta, pelo médico responsável.
- **Lista de espera**: só é permitida para horários **ocupados**. Quando o horário vaga (cancelamento ou
  remarcação), todos os pacientes que aguardam aquele horário são notificados em ordem de chegada (notificação
  interna + e-mail). Ao agendar o horário, a entrada passa para `agendado`. Entradas de horários que já passaram
  expiram.

### Atendimento
- Prontuário (queixa, diagnóstico, CID-10 opcional, observações), prescrições (medicamento, dosagem, frequência,
  duração) e exames só podem ser registrados pelo **médico responsável**, em consultas `em_andamento` ou `realizada`.
- Resultados de exames: texto e/ou arquivo **PDF, PNG ou JPEG** (até 10 MB). O conteúdo real do arquivo é verificado
  pela assinatura binária, o nome do arquivo é sanitizado e o armazenamento usa nome aleatório. O download é
  protegido contra *path traversal*.
- **Histórico clínico** do paciente: todas as consultas em ordem cronológica, com prontuário, prescrições e exames.

### Faturamento
- A cobrança refere-se a **uma** consulta **ou** um exame. Para consultas, o valor padrão é o valor de consulta do
  médico.
- **Desconto de convênio** aplicado automaticamente quando o paciente tem convênio ativo (arredondamento HALF_UP).
- Valores armazenados em centavos (inteiros) para evitar erros de ponto flutuante.
- No máximo uma cobrança ativa por item (verificada na aplicação e por índice único parcial).
- **Pagamento em dobro é impedido** com uma atualização condicional atômica (`WHERE status = 'pendente'`); pagar
  de novo retorna 409 `cobranca_ja_paga`. Pagamento parcial não é aceito. Cobranças pagas não podem ser canceladas.

### Relatórios (administrador)
Período padrão: últimos 30 dias (`date_from`/`date_to` inclusivos).
- Consultas por período (dia/mês), por médico, por especialidade e por status (todos os status, inclusive zerados).
- Faturamento: total recebido, descontos, pendências, por forma de pagamento e por período.
- Taxa de faltas por médico = `faltas / (realizadas + faltas)`; cancelamentos não entram no cálculo.
- Pacientes mais atendidos (consultas realizadas).

---

## Endpoints

| Módulo            | Rotas principais (prefixo `/api/v1`) |
|-------------------|--------------------------------------|
| Autenticação      | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/change-password`, `/auth/forgot-password`, `/auth/reset-password`; `GET /auth/me` |
| Usuários          | `POST/GET /users`, `GET/PATCH /users/{id}`, `POST /users/{id}/unlock` |
| Convênios         | `POST/GET /insurances`, `GET/PATCH /insurances/{id}` |
| Pacientes         | `POST/GET /patients`, `GET /patients/me`, `GET/PATCH/DELETE /patients/{id}`, `GET /patients/{id}/clinical-history` |
| Profissionais     | `POST/GET /professionals`, `GET /professionals/specialties`, `GET/PATCH/DELETE /professionals/{id}`, `POST/GET /professionals/{id}/availability`, `DELETE /professionals/{id}/availability/{aid}`, `GET /professionals/{id}/available-slots`, `GET /professionals/{id}/agenda` |
| Consultas         | `POST/GET /appointments`, `GET /appointments/{id}`, `POST /appointments/{id}/confirm`, `/cancel`, `/reschedule`, `/start`, `/complete`, `/no-show` |
| Prontuário        | `POST/GET/PATCH /appointments/{id}/medical-record`, `POST/GET /appointments/{id}/prescriptions`, `POST/GET /appointments/{id}/exams` |
| Exames            | `GET /exams/{id}`, `POST /exams/{id}/result` (multipart), `GET /exams/{id}/result-file`, `POST /exams/{id}/cancel` |
| Lista de espera   | `POST/GET /waitlist`, `GET /waitlist/{id}`, `POST /waitlist/{id}/cancel` |
| Faturamento       | `POST/GET /billing/charges`, `GET /billing/charges/{id}`, `POST /billing/charges/{id}/pay`, `/cancel` |
| Relatórios        | `GET /reports/appointments/by-period`, `/by-professional`, `/by-specialty`, `/by-status`, `GET /reports/revenue`, `/no-show-rate`, `/top-patients` |
| Auditoria         | `GET /audit-logs` |
| Notificações      | `GET /notifications`, `POST /notifications/{id}/read`, `POST /notifications/read-all` |

Listagens aceitam `page`, `page_size` (máx. 100), `sort_by` (lista fechada de campos por recurso) e `sort_order`
(`asc`/`desc`), além de filtros específicos. Datas/horas são no fuso da clínica (`TIMEZONE`); horários com fuso
explícito (ex.: `...Z`) são convertidos.

---

## Erros e validação

Todas as respostas de erro seguem o mesmo formato:

```json
{
  "error": {
    "code": "horario_ocupado",
    "message": "O médico já possui uma consulta neste horário. Você pode entrar na lista de espera.",
    "details": {"lista_de_espera_disponivel": true}
  }
}
```

| HTTP | Quando |
|------|--------|
| 401  | token ausente/inválido/expirado/revogado, credenciais inválidas |
| 403  | perfil sem permissão ou fora do escopo (ex.: dados de outro paciente) |
| 404  | recurso inexistente |
| 409  | conflitos: horário ocupado, CPF/CRM/e-mail duplicado, cobrança já paga |
| 413 / 415 | arquivo muito grande / tipo de arquivo não suportado |
| 422  | dados inválidos (lista `details` com `field` e `message` em português) ou regra de negócio violada |
| 423  | conta temporariamente bloqueada |
| 500  | erro inesperado (detalhes apenas no log, com `X-Request-ID`) |

Os schemas de entrada rejeitam campos desconhecidos, removem espaços extras e normalizam dados (CPF, telefone, CEP,
CRM, e-mail em minúsculas, valores com 2 casas decimais).

---

## Testes

```bash
pytest                          # 353 testes (unitários + integração)
pytest --cov=app                # cobertura (~95%)
ruff check app tests            # lint
```

- **Unitários** (`tests/unit`): validadores (CPF, CRM, COREN, senha, telefone, CID-10), cálculo de desconto,
  hash/JWT, regras puras de agenda e transições, matriz de permissões, armazenamento de arquivos, e-mail,
  configuração e CLI.
- **Integração** (`tests/integration`): cada módulo via HTTP, com banco SQLite em memória isolado por teste,
  **relógio congelado** (resultados determinísticos) e caixa de e-mail falsa. Cobrem os fluxos principais, o controle
  de acesso por perfil e escopo, e casos de borda: bloqueio e desbloqueio por tempo, reutilização de refresh token,
  expiração do código de recuperação, conflitos, horários desalinhados ou passados, fuso horário, lista de espera,
  uploads maliciosos, arredondamento de desconto e condições de corrida (índices únicos e pagamento concorrente).

---

## Decisões de projeto e limitações

- **Esquema do banco**: criado com `create_all` na inicialização. Para evoluir o esquema em produção, recomenda-se
  adotar Alembic.
- **SQLite**: adequado ao escopo pedido. Foram ativados `foreign_keys`, `WAL` e `busy_timeout`. Para alta
  concorrência de escrita, migrar para PostgreSQL (o código usa apenas `strftime` como função específica, nos
  relatórios).
- **E-mails** são enviados somente após o *commit* da transação. Sem `SMTP_HOST`, são apenas registrados em log.
- **Lista de espera**: todos os interessados são notificados; quem agendar primeiro garante o horário. Não há
  reserva automática.
- **Rate limiting** e HTTPS devem ser providos pela infraestrutura (proxy reverso). O bloqueio por tentativas protege
  contas individuais contra força bruta.
- Ausências e feriados dos profissionais não são modelados: a disponibilidade é semanal. Para bloquear um dia, remova
  a faixa ou cancele as consultas.
