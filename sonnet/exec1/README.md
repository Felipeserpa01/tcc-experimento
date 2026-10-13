# Library Management API

API REST de gerenciamento de biblioteca construída com **FastAPI**, **SQLAlchemy** e **SQLite**.

## Estrutura de pastas

```
.
├── app/
│   ├── main.py            # criação da aplicação FastAPI, routers e exception handlers
│   ├── config.py           # configurações (JWT, regras de negócio, banco de dados)
│   ├── database.py         # engine, sessão e Base do SQLAlchemy
│   ├── models.py            # modelos ORM: User, Book, Loan
│   ├── schemas.py            # schemas Pydantic de entrada/saída
│   ├── auth.py                 # hashing de senha (bcrypt) e JWT
│   ├── dependencies.py          # get_current_user / get_current_librarian
│   └── routers/
│       ├── auth.py                # POST /auth/register, POST /auth/login
│       ├── users.py                # GET /users/me
│       ├── books.py                # CRUD + busca de livros
│       └── loans.py                # empréstimos, devoluções e multas
├── tests/
│   ├── conftest.py       # fixtures: client de teste com banco SQLite isolado por teste
│   ├── test_auth.py       # registro, login, JWT
│   ├── test_books.py       # CRUD e busca de livros, permissões
│   └── test_loans.py        # empréstimos, devoluções, limite de 3, multas
├── requirements.txt
└── pytest.ini
```

## Requisitos de negócio implementados

- **Autenticação**: registro/login com JWT (`OAuth2PasswordBearer`), senhas com hash `bcrypt`.
- **Papéis**: `bibliotecario` e `leitor`. Apenas bibliotecários podem criar/editar/remover livros e
  registrar empréstimos/devoluções. Leitores só podem consultar livros e seus próprios empréstimos.
- **Livros**: CRUD completo + busca por título/autor (parcial, case-insensitive). ISBN único.
  `available_quantity` é ajustado automaticamente quando `total_quantity` é alterado.
- **Empréstimos**:
  - Bloqueia empréstimo se não houver exemplares disponíveis (`available_quantity == 0`).
  - Limita cada leitor a no máximo 3 empréstimos ativos simultâneos (configurável).
  - Devolução calcula multa por atraso: `dias_de_atraso * valor_por_dia` (padrão R$1,00/dia).
  - `GET /loans/me` e `GET /loans/reader/{id}` listam empréstimos (com filtro `active_only`).
- **Erros**: respostas HTTP apropriadas (400, 401, 403, 404, 409, 422).

## Como rodar

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

A documentação interativa fica disponível em `http://127.0.0.1:8000/docs`.

O banco SQLite (`library.db`) é criado automaticamente na primeira execução.

## Como rodar os testes

```bash
pytest -v
```

Cada teste usa um arquivo SQLite temporário isolado (criado e removido pela fixture `client` em
`tests/conftest.py`), então os testes não interferem entre si nem no `library.db` de desenvolvimento.

## Fluxo de uso rápido

```bash
# 1. Registrar um bibliotecário
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "ana", "email": "ana@lib.com", "password": "senha123", "role": "bibliotecario"}'

# 2. Login (retorna access_token)
curl -X POST http://127.0.0.1:8000/auth/login \
  -d "username=ana&password=senha123"

# 3. Cadastrar um livro (usar o token no header Authorization: Bearer <token>)
curl -X POST http://127.0.0.1:8000/books/ \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"title": "Dom Casmurro", "author": "Machado de Assis", "isbn": "9788535910663", "year": 1899, "total_quantity": 3}'

# 4. Registrar um empréstimo
curl -X POST http://127.0.0.1:8000/loans/ \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"book_id": 1, "reader_id": 2}'

# 5. Registrar devolução (calcula multa automaticamente se atrasado)
curl -X POST http://127.0.0.1:8000/loans/1/return -H "Authorization: Bearer <TOKEN>"
```

## Variáveis de ambiente (opcionais)

| Variável                       | Padrão                          | Descrição                                  |
|--------------------------------|----------------------------------|---------------------------------------------|
| `DATABASE_URL`                 | `sqlite:///./library.db`         | URL de conexão do banco                     |
| `SECRET_KEY`                   | valor de desenvolvimento         | chave usada para assinar os JWT             |
| `ACCESS_TOKEN_EXPIRE_MINUTES`  | `60`                              | validade do token de acesso                 |
| `LOAN_PERIOD_DAYS`              | `14`                              | prazo padrão de empréstimo, em dias         |
| `FINE_PER_DAY`                  | `1.00`                            | valor da multa por dia de atraso            |
| `MAX_ACTIVE_LOANS_PER_READER`   | `3`                               | limite de empréstimos simultâneos por leitor |
