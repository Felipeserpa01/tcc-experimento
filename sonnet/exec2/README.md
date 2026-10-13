# Library Management API

API REST de gerenciamento de biblioteca construída com **FastAPI**, **SQLAlchemy** e **SQLite**.

## Estrutura de pastas

```
.
├── app/
│   ├── main.py            # criação da aplicação FastAPI, rotas e handlers de erro
│   ├── config.py          # configurações via variáveis de ambiente
│   ├── database.py        # engine, sessão e Base do SQLAlchemy
│   ├── models.py          # modelos ORM: User, Book, Loan
│   ├── schemas.py         # schemas Pydantic (request/response)
│   ├── auth.py            # hashing de senha (bcrypt) e JWT
│   ├── dependencies.py    # dependências de autenticação/autorização
│   └── routers/
│       ├── auth.py        # /auth/register, /auth/login
│       ├── books.py       # CRUD e busca de livros
│       └── loans.py       # empréstimos, devoluções e multas
├── tests/
│   ├── conftest.py        # fixtures (client, usuários, banco de testes isolado)
│   ├── test_auth.py
│   ├── test_books.py
│   └── test_loans.py
├── requirements.txt
└── README.md
```

## Como executar

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

A API sobe em `http://127.0.0.1:8000`. Documentação interativa em `/docs` (Swagger) ou `/redoc`.

Um arquivo `library.db` (SQLite) é criado automaticamente na primeira execução.

### Variáveis de ambiente (opcionais)

| Variável                     | Padrão                        | Descrição                                  |
|-------------------------------|-------------------------------|---------------------------------------------|
| `DATABASE_URL`                | `sqlite:///./library.db`      | URL de conexão do banco                     |
| `SECRET_KEY`                  | chave de desenvolvimento      | chave usada para assinar os tokens JWT      |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                          | validade do token JWT                       |
| `LOAN_PERIOD_DAYS`            | `14`                          | prazo padrão de devolução do empréstimo     |
| `FINE_PER_DAY`                | `1.0`                         | valor da multa por dia de atraso            |
| `MAX_LOANS_PER_READER`        | `3`                           | limite de empréstimos simultâneos por leitor|

Em produção, defina `SECRET_KEY` com um valor forte e aleatório.

## Rodando os testes

```bash
pytest -v
```

Os testes usam um banco SQLite em memória isolado (não afetam `library.db`).

## Autenticação

- `POST /auth/register` — cria um usuário (`role`: `"librarian"` ou `"reader"`). Senha é armazenada com hash bcrypt.
- `POST /auth/login` — recebe `username`/`password` (form `x-www-form-urlencoded`, padrão OAuth2) e retorna um JWT (`access_token`).
- Rotas protegidas exigem o header `Authorization: Bearer <token>`.

## Papéis e permissões

| Ação                                   | Bibliotecário | Leitor |
|-----------------------------------------|:-------------:|:------:|
| Cadastrar/atualizar/remover livro       | ✅            | ❌     |
| Listar/buscar/ver livro                 | ✅            | ✅     |
| Registrar empréstimo                    | ✅            | ❌     |
| Registrar devolução                     | ✅            | ❌     |
| Listar todos os empréstimos             | ✅            | ❌     |
| Ver os próprios empréstimos (`/loans/me`)| ✅           | ✅     |
| Ver empréstimos ativos de um leitor específico | ✅ (qualquer leitor) | ✅ (apenas os próprios) |

## Principais endpoints

### Livros
- `POST /books/` — cadastra livro (bibliotecário)
- `GET /books/?q=<termo>&skip=&limit=` — lista/busca por título ou autor
- `GET /books/{book_id}` — detalhe de um livro
- `PUT /books/{book_id}` — atualiza campos do livro (bibliotecário)
- `DELETE /books/{book_id}` — remove livro, bloqueado se houver empréstimos ativos (bibliotecário)

### Empréstimos
- `POST /loans/` — registra empréstimo de `book_id` para `reader_id` (bibliotecário). Bloqueia se não houver exemplar disponível ou se o leitor já tiver `MAX_LOANS_PER_READER` empréstimos ativos.
- `PUT /loans/{loan_id}/return` — registra devolução, calcula multa por atraso (`FINE_PER_DAY` × dias de atraso) e devolve o exemplar ao acervo (bibliotecário).
- `GET /loans/` — lista todos os empréstimos, com filtros `reader_id` e `active_only` (bibliotecário).
- `GET /loans/me?active_only=` — empréstimos do próprio usuário autenticado.
- `GET /loans/reader/{reader_id}/active` — empréstimos ativos de um leitor (bibliotecário vê qualquer um; leitor só vê os próprios).

## Regras de negócio implementadas

- Um livro só pode ser emprestado se `available_copies > 0`.
- Um leitor não pode ter mais de `MAX_LOANS_PER_READER` (padrão 3) empréstimos simultâneos (não devolvidos).
- A data de vencimento é calculada automaticamente como `data do empréstimo + LOAN_PERIOD_DAYS`.
- A multa é calculada na devolução como `max(0, dias de atraso) × FINE_PER_DAY`.
- Um livro não pode ser removido enquanto tiver exemplares emprestados.
- Erros de negócio retornam códigos HTTP apropriados (`400`, `401`, `403`, `404`, `409`) com mensagens descritivas.
