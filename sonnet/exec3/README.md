# API de Gerenciamento de Biblioteca

API REST construída com **FastAPI** para gerenciamento de livros, usuários e empréstimos de uma biblioteca.

## Estrutura do projeto

```
.
├── app/
│   ├── main.py            # Criação da aplicação FastAPI e inclusão das rotas
│   ├── database.py         # Configuração do SQLAlchemy / SQLite
│   ├── models.py            # Modelos ORM (User, Book, Loan)
│   ├── schemas.py            # Schemas Pydantic (validação de entrada/saída)
│   ├── auth.py                 # Hash de senha (bcrypt) e JWT (PyJWT)
│   ├── dependencies.py           # Dependências de autenticação/autorização
│   └── routers/
│       ├── auth.py                # /auth (registro, login, usuário atual)
│       ├── books.py                # /books (CRUD e busca)
│       └── loans.py                # /loans (empréstimos e devoluções)
├── tests/
│   ├── conftest.py         # Fixtures de teste (DB isolado, usuários, livro de exemplo)
│   ├── test_auth.py
│   ├── test_books.py
│   └── test_loans.py
├── requirements.txt
└── pytest.ini
```

## Como executar

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

A documentação interativa fica disponível em `http://localhost:8000/docs` (Swagger UI) e `http://localhost:8000/redoc`.

O banco SQLite é criado automaticamente em `library.db` na primeira execução.

### Variáveis de ambiente (opcionais)

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./library.db` | URL de conexão do banco |
| `SECRET_KEY` | chave de desenvolvimento | Chave usada para assinar os tokens JWT — **defina uma chave própria em produção** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Tempo de expiração do token JWT |

## Como rodar os testes

```bash
pytest -v
```

Os testes usam um banco SQLite temporário isolado (criado em `tests/conftest.py`), portanto não afetam o `library.db` de desenvolvimento.

## Autenticação

- `POST /auth/register` — cria um usuário (`role`: `bibliotecario` ou `leitor`, padrão `leitor`)
- `POST /auth/login` — autentica via `username`/`password` (form OAuth2) e retorna um JWT
- `GET /auth/me` — retorna os dados do usuário autenticado

Envie o token nas rotas protegidas com o header `Authorization: Bearer <token>`.

## Livros

- `POST /books/` — cadastra um livro (somente bibliotecário). `available_quantity` é definida automaticamente como `total_quantity` no cadastro.
- `GET /books/?search=&skip=&limit=` — lista/busca livros por título ou autor (qualquer usuário autenticado)
- `GET /books/{id}` — detalhes de um livro
- `PUT /books/{id}` — atualiza um livro (somente bibliotecário). Alterar `total_quantity` ajusta `available_quantity` proporcionalmente e é bloqueado se deixaria o valor negativo (exemplares emprestados).
- `DELETE /books/{id}` — remove um livro (somente bibliotecário; bloqueado se houver empréstimos ativos)

## Empréstimos

- `POST /loans/` — registra um empréstimo (somente bibliotecário). Regras aplicadas:
  - o livro precisa ter `available_quantity >= 1`
  - o leitor não pode ter mais que **3 empréstimos ativos simultâneos**
  - o prazo de devolução é de **14 dias** a partir do empréstimo
- `POST /loans/{id}/return` — registra a devolução (somente bibliotecário) e calcula a multa por atraso (**R$1,00 por dia de atraso**, comparando a data prevista com a data real)
- `GET /loans/` — lista todos os empréstimos (somente bibliotecário; `?active_only=true` filtra os ativos)
- `GET /loans/me` — lista os empréstimos do usuário autenticado (por padrão, apenas ativos)
- `GET /loans/reader/{reader_id}` — lista os empréstimos de um leitor específico (o próprio leitor ou um bibliotecário)

## Segurança

- Senhas são armazenadas com hash **bcrypt** (nunca em texto puro)
- Autenticação via **JWT** (PyJWT, HS256)
- Autorização baseada em papel (`bibliotecario` / `leitor`) aplicada por dependências do FastAPI
