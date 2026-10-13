# Library Management API

Uma API REST completa para gerenciamento de biblioteca desenvolvida com Python e FastAPI.

## Recursos

- ✅ Autenticação com JWT
- ✅ Dois tipos de usuário: Bibliotecário e Leitor
- ✅ CRUD completo de livros
- ✅ Sistema de empréstimos e devoluções
- ✅ Cálculo automático de multas por atraso
- ✅ Limite de 3 empréstimos simultâneos por leitor
- ✅ Testes unitários com pytest
- ✅ Banco de dados SQLite

## Instalação

### Pré-requisitos
- Python 3.9+
- pip

### Passos

1. Clone ou baixe o projeto:
```bash
cd library-api
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Executar a aplicação

```bash
uvicorn app.main:app --reload
```

A API estará disponível em: `http://localhost:8000`

Documentação interativa (Swagger UI): `http://localhost:8000/docs`

## Estrutura de pastas

```
library-api/
├── app/
│   ├── models/              # Modelos SQLAlchemy
│   │   ├── user.py
│   │   ├── book.py
│   │   └── loan.py
│   ├── schemas/             # Schemas Pydantic
│   │   ├── user.py
│   │   ├── book.py
│   │   └── loan.py
│   ├── crud/                # Operações CRUD
│   │   ├── user.py
│   │   ├── book.py
│   │   └── loan.py
│   ├── routes/              # Endpoints da API
│   │   ├── auth.py
│   │   ├── books.py
│   │   └── loans.py
│   ├── database.py          # Configuração do banco
│   ├── security.py          # Autenticação JWT
│   └── main.py              # Aplicação principal
├── tests/                   # Testes unitários
│   ├── test_auth.py
│   ├── test_books.py
│   ├── test_loans.py
│   └── conftest.py
├── requirements.txt
└── README.md
```

## Endpoints

### Autenticação

#### Registrar novo usuário
```http
POST /auth/register
Content-Type: application/json

{
  "email": "usuario@example.com",
  "full_name": "Nome do Usuário",
  "password": "senha123",
  "role": "reader"  # "reader" ou "librarian"
}
```

#### Fazer login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "usuario@example.com",
  "password": "senha123"
}

Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {...}
}
```

### Livros (CRUD)

#### Criar livro (apenas bibliotecário)
```http
POST /books/
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Python Basics",
  "author": "John Doe",
  "isbn": "978-1234567890",
  "year": 2023,
  "total_quantity": 5
}
```

#### Listar livros
```http
GET /books/?skip=0&limit=10
Authorization: Bearer {token}
```

#### Buscar livros
```http
GET /books/search?q=python
Authorization: Bearer {token}
```

#### Obter detalhes do livro
```http
GET /books/{book_id}
Authorization: Bearer {token}
```

#### Atualizar livro (apenas bibliotecário)
```http
PUT /books/{book_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Python Advanced",
  "year": 2024
}
```

#### Deletar livro (apenas bibliotecário)
```http
DELETE /books/{book_id}
Authorization: Bearer {token}
```

### Empréstimos

#### Emprestar um livro
```http
POST /loans/
Authorization: Bearer {token}
Content-Type: application/json

{
  "book_id": 1
}
```

Regras:
- Apenas leitores podem emprestar
- Máximo 3 empréstimos simultâneos
- Prazo de devolução: 14 dias
- Livro não disponível retorna erro

#### Listar empréstimos ativos
```http
GET /loans/
Authorization: Bearer {token}
```

Apenas o leitor autenticado pode listar seus empréstimos.

#### Devolver livro
```http
POST /loans/{loan_id}/return
Authorization: Bearer {token}
Content-Type: application/json

{
  "return_date": "2024-01-15T10:30:00"
}
```

Cálculo de multa:
- Multa por atraso: R$ 5,00 por dia
- A multa é calculada automaticamente se a devolução for após a data prevista

## Tipos de usuários

### Bibliotecário (librarian)
- Pode criar, listar, atualizar e deletar livros
- Pode processar devoluções de qualquer leitor
- Não pode emprestar livros

### Leitor (reader)
- Pode listar e buscar livros
- Pode emprestar livros (máximo 3 simultâneos)
- Pode devolver seus próprios livros
- Pode visualizar seus empréstimos ativos

## Testes

Executar todos os testes:
```bash
pytest
```

Executar com cobertura:
```bash
pytest --cov=app tests/
```

Testes incluem:
- ✅ Autenticação (registro, login, validações)
- ✅ Livros (CRUD, busca, validações)
- ✅ Empréstimos (criar, devolver, limite de 3, multas)

## Segurança

- Senhas são hasheadas com bcrypt
- Autenticação JWT com token expiração de 30 minutos
- Validação de entrada com Pydantic
- Proteção de endpoints por role

## Banco de dados

O banco de dados SQLite é criado automaticamente ao iniciar a aplicação.

Para resetar o banco:
```bash
rm library.db
```

## Desenvolvido com

- FastAPI - Framework web moderno
- SQLAlchemy - ORM para banco de dados
- Pydantic - Validação de dados
- python-jose - JWT
- passlib - Hashing de senhas
- pytest - Testes unitários
