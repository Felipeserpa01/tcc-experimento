# API de Gerenciamento de Biblioteca

API REST em **Python + FastAPI** para gerenciar uma biblioteca: usuários (bibliotecários e leitores), acervo de livros e empréstimos com cálculo de multa por atraso.

**Stack:** FastAPI · SQLAlchemy 2.0 · SQLite · Pydantic v2 · JWT (PyJWT) · bcrypt · pytest

---

## Estrutura do projeto

```
.
├── app/
│   ├── main.py                 # Criação da aplicação, rotas e ciclo de vida
│   ├── cli.py                  # Comando para criar o primeiro bibliotecário
│   ├── api/
│   │   ├── deps.py             # Dependências: sessão, usuário autenticado, papéis, relógio, paginação
│   │   ├── error_handlers.py   # Conversão de exceções em respostas HTTP
│   │   └── routes/             # auth.py, users.py, books.py, loans.py
│   ├── core/
│   │   ├── config.py           # Configurações via variáveis de ambiente / .env
│   │   ├── security.py         # Hash de senhas (bcrypt) e tokens JWT
│   │   └── exceptions.py       # Exceções de domínio (404, 409, ...)
│   ├── db/
│   │   ├── base.py             # Base declarativa e tipo de datetime em UTC
│   │   └── session.py          # Engine SQLite, sessão e criação das tabelas
│   ├── models/                 # Modelos ORM: User, Book, Loan
│   ├── schemas/                # Schemas Pydantic (validação de entrada e saída)
│   ├── services/               # Regras de negócio
│   │   ├── user_service.py
│   │   ├── book_service.py
│   │   ├── loan_service.py
│   │   └── fines.py            # Cálculo de multa (funções puras)
│   └── utils/                  # ISBN, normalização de texto, datas
├── tests/
│   ├── conftest.py             # Fixtures: banco isolado por teste, relógio controlável, fábricas
│   ├── unit/                   # Multas, segurança, validações, serviço de empréstimos, CLI
│   └── api/                    # Testes de integração dos endpoints
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── .env.example
```

As rotas só recebem a requisição e delegam; as regras ficam em `services/`, que não dependem do FastAPI e são testadas diretamente.

---

## Como executar

Requer **Python 3.11+**.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env               # opcional; defina SECRET_KEY para produção

# Crie o primeiro bibliotecário (a senha é pedida no terminal)
python -m app.cli create-librarian --name "Maria Lima" --email maria@biblioteca.com

uvicorn app.main:app --reload
```

- Documentação interativa (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

As tabelas são criadas automaticamente no arquivo `library.db` ao iniciar.

### Testes

```bash
pytest                              # 119 testes
pytest --cov=app --cov-report=term-missing
```

Cada teste usa um banco SQLite próprio em diretório temporário. O banco real não é tocado.

---

## Autenticação

1. Leitores se cadastram em `POST /auth/register`.
2. O login em `POST /auth/login` retorna um JWT:
   ```json
   { "access_token": "eyJ...", "token_type": "bearer", "expires_in": 3600 }
   ```
3. Envie o token no cabeçalho `Authorization: Bearer <token>`.

No Swagger, use o botão **Authorize**, com o e-mail no campo `username`. Ele usa `POST /auth/token`, o formulário OAuth2.

**Tipos de usuário**

| Papel | Valor | Pode |
|---|---|---|
| Bibliotecário | `librarian` | Tudo: gerenciar livros, registrar empréstimos e devoluções, consultar qualquer usuário e cadastrar outros bibliotecários |
| Leitor | `reader` | Consultar e buscar livros, ver os próprios dados e empréstimos |

Por segurança, **ninguém se cadastra como bibliotecário sem autenticação**. O primeiro é criado pela CLI e os demais por um bibliotecário autenticado.

**Senhas:** hash com bcrypt e salt individual. Exigem no mínimo 8 caracteres, com ao menos uma letra e um número. O login devolve a mesma mensagem e leva o mesmo tempo para e-mail inexistente e senha errada, para não revelar quais e-mails estão cadastrados.

---

## Endpoints

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/auth/register` | Público (leitor) / Bibliotecário | Cadastro de usuário |
| POST | `/auth/login` | Público | Login com JSON |
| POST | `/auth/token` | Público | Login com formulário OAuth2 (Swagger) |
| GET | `/users/me` | Autenticado | Dados do usuário logado |
| GET | `/users/me/loans/active` | Leitor | Meus empréstimos ativos |
| GET | `/users` | Bibliotecário | Lista usuários (`?role=reader`) |
| GET | `/users/{id}` | Bibliotecário ou o próprio | Consulta usuário |
| GET | `/users/{id}/loans/active` | Bibliotecário ou o próprio | **Empréstimos ativos de um leitor** |
| POST | `/books` | Bibliotecário | Cadastra livro |
| GET | `/books` | Autenticado | Lista e busca livros (`?q=`, `?title=`, `?author=`, `?available=`) |
| GET | `/books/{id}` | Autenticado | Consulta livro |
| PATCH | `/books/{id}` | Bibliotecário | Atualização parcial |
| DELETE | `/books/{id}` | Bibliotecário | Remove livro |
| POST | `/loans` | Bibliotecário | **Registra empréstimo** |
| POST | `/loans/{id}/return` | Bibliotecário | **Registra devolução e calcula a multa** |
| GET | `/loans` | Bibliotecário (todos) / Leitor (os seus) | Lista empréstimos (`?reader_id=`, `?book_id=`, `?status=active\|overdue\|returned`) |
| GET | `/loans/{id}` | Bibliotecário ou o leitor do empréstimo | Consulta empréstimo |
| GET | `/health` | Público | Verificação de saúde |

As listagens são paginadas com `?skip=0&limit=20` (máximo de 100) e retornam `{ items, total, skip, limit }`.

---

## Regras de negócio

### Livros
- Campos: `title`, `author`, `isbn`, `year`, `total_quantity` e `available_quantity`.
- `available_quantity` não é enviada pelo cliente. No cadastro ela é igual ao total e depois muda com empréstimos e devoluções.
- O **ISBN** aceita ISBN-10 ou ISBN-13, com ou sem hífens, e tem o dígito verificador conferido. É armazenado sempre como ISBN-13, então `0-306-40615-2` e `978-0-306-40615-7` contam como o mesmo livro e são barrados como duplicata.
- Ao alterar `total_quantity`, a disponível é ajustada mantendo os exemplares emprestados. Não é permitido reduzir o total abaixo do número de exemplares emprestados (409).
- A **busca** é parcial e ignora maiúsculas/minúsculas e acentos: `jose saramago` encontra "José Saramago".
- Não é possível remover livro com empréstimo ativo (409). O histórico de empréstimos já devolvidos é removido junto com o livro.

### Empréstimos
- Apenas usuários do tipo **leitor** podem receber empréstimos (400 caso contrário).
- **Sem exemplares disponíveis → 409** (`book_unavailable`).
- **Máximo de 3 empréstimos simultâneos por leitor → 409** (`loan_limit_reached`). Empréstimos devolvidos não contam.
- Prazo padrão de 14 dias, que pode ser alterado por empréstimo com `loan_days` (1 a 60).
- Devolver duas vezes → 409 (`loan_already_returned`).
- Empréstimo e devolução usam `UPDATE`s condicionais no banco. Assim, duas requisições simultâneas não emprestam o último exemplar duas vezes nem devolvem o mesmo exemplar ao estoque em dobro. Há testes que simulam essas corridas.

### Multa por atraso
```
dias_de_atraso = max(0, data_real_de_devolução − data_prevista)
multa          = dias_de_atraso × multa_diária     (padrão: R$ 2,00)
```
- Devolver até a data prevista, inclusive, não gera multa.
- A multa é **fixada na devolução** e guardada em centavos. Mudar a multa diária depois não altera valores já cobrados.
- Empréstimos em aberto e atrasados mostram `status: "overdue"`, os `days_overdue` e a multa acumulada até hoje.
- As datas são contadas no calendário do fuso da biblioteca (`America/Sao_Paulo`). Um empréstimo feito às 22h pertence àquele dia, mesmo que em UTC já seja o dia seguinte.

Exemplo de resposta de devolução com atraso:
```json
{
  "id": 7,
  "book": { "id": 3, "title": "Dom Casmurro", "author": "Machado de Assis", "isbn": "9780306406157" },
  "reader": { "id": 2, "name": "João", "email": "joao@example.com" },
  "loan_date": "2026-03-02T12:00:00Z",
  "due_date": "2026-03-09",
  "returned_at": "2026-03-14T12:00:00Z",
  "status": "returned",
  "days_overdue": 5,
  "fine_amount": 10.0
}
```

---

## Erros

Erros de negócio seguem um formato único, com mensagem legível e um código estável para o cliente tratar:

```json
{ "detail": "O leitor já atingiu o limite de 3 empréstimos simultâneos", "code": "loan_limit_reached" }
```

| Status | Quando |
|---|---|
| 400 | Operação inválida (ex.: emprestar para um bibliotecário) |
| 401 | Token ausente, inválido ou expirado; credenciais incorretas |
| 403 | Papel sem permissão ou acesso a dados de outro leitor |
| 404 | Recurso não encontrado |
| 409 | Conflito de estado: e-mail/ISBN duplicado, sem estoque, limite de empréstimos, já devolvido |
| 422 | Dados de entrada inválidos (formato padrão do FastAPI, com o campo em `loc`) |

Na validação, os campos numéricos do corpo são estritos (`"3"` não é aceito como `3`) e campos desconhecidos são rejeitados.

---

## Configuração

Por variáveis de ambiente ou arquivo `.env` (veja `.env.example`):

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | aleatória a cada início | Chave de assinatura do JWT, com no mínimo 32 caracteres. **Defina em produção.** |
| `DATABASE_URL` | `sqlite:///./library.db` | Banco de dados |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Validade do token |
| `BCRYPT_ROUNDS` | `12` | Custo do hash de senha |
| `MAX_ACTIVE_LOANS` | `3` | Empréstimos simultâneos por leitor |
| `DEFAULT_LOAN_DAYS` / `MAX_LOAN_DAYS` | `14` / `60` | Prazos de empréstimo |
| `DAILY_FINE` | `2.00` | Multa por dia de atraso |
| `LIBRARY_TIMEZONE` | `America/Sao_Paulo` | Fuso usado para datas previstas e atraso |

## Possíveis evoluções
- Migrações de schema com Alembic (hoje as tabelas são criadas com `create_all`).
- Registro de pagamento de multas e bloqueio de novos empréstimos para leitores com multa pendente.
- Renovação de empréstimos e fila de reservas.
