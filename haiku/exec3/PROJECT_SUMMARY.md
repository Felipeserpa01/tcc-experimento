# 📚 Biblioteca API - Resumo do Projeto

## ✅ Status: Concluído

Uma API REST completa para gerenciamento de biblioteca desenvolvida com **FastAPI**, **SQLAlchemy** e **SQLite**.

---

## 📊 Resumo Executivo

| Métrica | Valor |
|---------|-------|
| **Testes Unitários** | 28 testes ✅ |
| **Cobertura** | Autenticação, Livros, Empréstimos |
| **Endpoints** | 15+ endpoints implementados |
| **Modelos** | 3 modelos principais (User, Book, Loan) |
| **Autenticação** | JWT com access/refresh tokens |
| **Banco de Dados** | SQLite com SQLAlchemy ORM |

---

## 🏗️ Arquitetura do Projeto

### Estrutura de Diretórios

```
biblioteca/
├── app/
│   ├── main.py              # FastAPI app e rotas principais
│   ├── database.py          # Configuração SQLAlchemy
│   ├── config.py            # Settings globais
│   │
│   ├── models/              # Modelos de banco de dados
│   │   ├── user.py          # User (Bibliotecário/Leitor)
│   │   ├── book.py          # Book (ISBN, título, autor...)
│   │   └── loan.py          # Loan (Empréstimos com multa)
│   │
│   ├── schemas/             # Validação Pydantic
│   │   ├── user.py          # UserCreate, UserResponse, TokenResponse
│   │   ├── book.py          # BookCreate, BookResponse, BookUpdate
│   │   └── loan.py          # LoanCreate, LoanResponse, LoanReturn
│   │
│   ├── routes/              # Endpoints da API
│   │   ├── auth.py          # /auth/register, /auth/login
│   │   ├── books.py         # CRUD de livros
│   │   └── loans.py         # Empréstimos e devoluções
│   │
│   ├── security/            # Autenticação
│   │   └── jwt.py           # Geração e validação de tokens
│   │
│   └── utils/               # Utilitários
│       └── validators.py    # Email, ISBN, senha, username
│
├── tests/                   # Testes com pytest
│   ├── conftest.py          # Setup de testes
│   ├── test_auth.py         # 7 testes de autenticação
│   ├── test_books.py        # 11 testes de livros
│   └── test_loans.py        # 10 testes de empréstimos
│
├── requirements.txt         # Dependências Python
├── README.md                # Documentação completa
├── QUICKSTART.md            # Guia rápido
└── example_usage.py         # Script de demonstração
```

---

## 🔐 Autenticação JWT

```python
# Token inclui:
{
  "sub": "user_id",
  "username": "nome_usuario",
  "user_type": "reader|librarian",
  "exp": timestamp
}
```

**Endpoints:**
- `POST /auth/register` - Registrar novo usuário
- `POST /auth/login` - Fazer login e obter tokens

---

## 📖 Gerenciamento de Livros

### Modelos de Dados

```python
Book {
  id: int
  title: str
  author: str
  isbn: str (validado)
  year: int (1000-2100)
  total_quantity: int
  available_quantity: int (atualizado automaticamente)
  description: str (opcional)
}
```

### Operações (CRUD)

| Operação | Endpoint | Permissão | Teste |
|----------|----------|-----------|-------|
| **Create** | `POST /books/` | Bibliotecário | ✅ |
| **Read** | `GET /books/` | Qualquer um | ✅ |
| **Read** | `GET /books/{id}` | Qualquer um | ✅ |
| **Search** | `GET /books/search?title=X` | Qualquer um | ✅ |
| **Search** | `GET /books/search?author=X` | Qualquer um | ✅ |
| **Update** | `PUT /books/{id}` | Bibliotecário | ✅ |
| **Delete** | `DELETE /books/{id}` | Bibliotecário | ✅ |

**Validações:**
- ISBN válido (10 ou 13 dígitos)
- Ano entre 1000 e 2100
- Quantidade não negativa
- ISBN único

---

## 🎫 Gerenciamento de Empréstimos

### Modelos de Dados

```python
Loan {
  id: int
  user_id: int (FK)
  book_id: int (FK)
  loan_date: datetime
  due_date: datetime (14 dias por padrão)
  return_date: datetime (null se ativo)
  status: "active" | "returned" | "overdue"
  fine_amount: float (calculado automaticamente)
}
```

### Operações

| Operação | Endpoint | Teste |
|----------|----------|-------|
| **Emprestar** | `POST /loans/` | ✅ |
| **Devolver** | `POST /loans/return` | ✅ |
| **Listar Ativos** | `GET /loans/user/active` | ✅ |
| **Consultar** | `GET /loans/{id}` | ✅ |

### Regras de Negócio

1. **Disponibilidade**: Não pode emprestar sem exemplares disponíveis ✅
2. **Limite**: Máximo 3 empréstimos simultâneos por leitor ✅
3. **Duração**: 14 dias para devolver ✅
4. **Multa**: R$ 5,00 por dia de atraso ✅
5. **Quantidade**: Decrementada ao emprestar, incrementada ao devolver ✅

**Exemplos de Testes:**
```python
✅ test_create_loan_success
✅ test_create_loan_book_not_available
✅ test_create_loan_max_loans_exceeded
✅ test_return_loan_on_time
✅ test_return_loan_overdue
✅ test_book_availability_updated_on_loan
✅ test_book_availability_restored_on_return
```

---

## 👥 Tipos de Usuário

### Bibliotecário
- ✅ Criar livros
- ✅ Atualizar livros
- ✅ Deletar livros
- ✅ Visualizar empréstimos
- ✅ Registrar livros

### Leitor
- ✅ Visualizar livros
- ✅ Buscar livros
- ✅ Emprestar livros
- ✅ Devolver livros
- ✅ Ver seus empréstimos

---

## 🧪 Testes Unitários

### Cobertura de Testes

```
tests/test_auth.py (7 testes)
  ✅ test_register_user_success
  ✅ test_register_invalid_username
  ✅ test_register_weak_password
  ✅ test_register_duplicate_username
  ✅ test_login_success
  ✅ test_login_invalid_credentials
  ✅ test_login_nonexistent_user

tests/test_books.py (11 testes)
  ✅ test_create_book_success
  ✅ test_create_book_invalid_isbn
  ✅ test_create_book_duplicate_isbn
  ✅ test_create_book_reader_cannot
  ✅ test_list_books
  ✅ test_search_books_by_title
  ✅ test_search_books_by_author
  ✅ test_get_book
  ✅ test_get_nonexistent_book
  ✅ test_update_book
  ✅ test_delete_book

tests/test_loans.py (10 testes)
  ✅ test_create_loan_success
  ✅ test_create_loan_book_not_available
  ✅ test_create_loan_max_loans_exceeded
  ✅ test_return_loan_on_time
  ✅ test_return_loan_overdue
  ✅ test_get_active_loans
  ✅ test_get_loan_unauthorized
  ✅ test_return_loan_not_found
  ✅ test_book_availability_updated_on_loan
  ✅ test_book_availability_restored_on_return

Total: 28/28 PASSANDO ✅
```

### Executar Testes

```bash
# Todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=app

# Teste específico
pytest tests/test_auth.py -v
```

---

## 🔒 Validações Implementadas

### Usuários
- Username: 3-50 caracteres, alfanumérico + hífen/underscore
- Email: Formato válido
- Senha: Mín 8 caracteres, maiúscula, minúscula, número
- Criptografia: bcrypt

### Livros
- ISBN: Válido (10 ou 13 dígitos)
- Ano: 1000-2100
- Título: Não vazio
- Autor: Não vazio
- Quantidade: ≥ 0

### Empréstimos
- Livro disponível
- Leitor não excedeu limite
- Devolução apenas de empréstimo ativo
- Acesso apenas ao próprio empréstimo

---

## 📋 Endpoints Completos

### Autenticação
```
POST   /auth/register          Registrar usuário
POST   /auth/login             Fazer login
```

### Livros
```
POST   /books/                 Criar livro
GET    /books/                 Listar livros
GET    /books/search           Buscar livros
GET    /books/{id}             Obter livro
PUT    /books/{id}             Atualizar livro
DELETE /books/{id}             Deletar livro
```

### Empréstimos
```
POST   /loans/                 Criar empréstimo
GET    /loans/                 Listar empréstimos
GET    /loans/user/active      Empréstimos ativos
GET    /loans/{id}             Obter empréstimo
POST   /loans/return           Devolver livro
```

### Utilitário
```
GET    /                       Info da API
GET    /health                 Health check
GET    /docs                   Documentação Swagger
GET    /redoc                  ReDoc
```

---

## 📦 Dependências

```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
```

---

## 🚀 Como Usar

### 1. Instalação
```bash
pip install -r requirements.txt
```

### 2. Rodar a Aplicação
```bash
uvicorn app.main:app --reload
```

### 3. Acessar
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 4. Testar
```bash
pytest tests/ -v
```

---

## 💡 Recursos Adicionais

- ✅ Documentação automática (Swagger)
- ✅ Script de demonstração (example_usage.py)
- ✅ Validação robusta de entrada
- ✅ Tratamento de erros completo
- ✅ CORS habilitado
- ✅ Timestamps automáticos
- ✅ Qualidades isoladas por teste (conftest.py)

---

## 📝 Exemplo de Uso Prático

```bash
# 1. Registrar como bibliotecário
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "maria_lib",
    "email": "maria@lib.com",
    "password": "Senha123",
    "user_type": "librarian"
  }'

# 2. Fazer login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "maria_lib", "password": "Senha123"}'

# 3. Criar um livro (como bibliotecário)
TOKEN="eyJhbGc..."
curl -X POST "http://localhost:8000/books/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Clean Code",
    "author": "Robert Martin",
    "isbn": "978-0132350884",
    "year": 2008,
    "total_quantity": 5
  }'

# 4. Registrar como leitor
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "joao_leitor",
    "email": "joao@email.com",
    "password": "Senha456",
    "user_type": "reader"
  }'

# 5. Fazer login como leitor
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "joao_leitor", "password": "Senha456"}'

# 6. Emprestar um livro
READER_TOKEN="eyJhbGc..."
curl -X POST "http://localhost:8000/loans/" \
  -H "Authorization: Bearer $READER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 1}'

# 7. Ver empréstimos ativos
curl -X GET "http://localhost:8000/loans/user/active" \
  -H "Authorization: Bearer $READER_TOKEN"

# 8. Devolver livro
curl -X POST "http://localhost:8000/loans/return" \
  -H "Authorization: Bearer $READER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"loan_id": 1}'
```

---

## ✨ Diferenciais Implementados

1. ✅ **Dois Tipos de Usuário**: Bibliotecário e Leitor com permissões distintas
2. ✅ **Criptografia de Senha**: Bcrypt com validação de força
3. ✅ **JWT Duplo**: Access Token + Refresh Token
4. ✅ **Validação Robusta**: ISBN, Email, Senha, Username
5. ✅ **Controle de Quantidade**: Atualizado automaticamente
6. ✅ **Limite de Empréstimos**: Máximo 3 simultâneos
7. ✅ **Cálculo de Multa**: R$ 5,00 por dia de atraso
8. ✅ **Testes Completos**: 28 testes cobrindo todos os cenários
9. ✅ **Documentação Automática**: Swagger/OpenAPI
10. ✅ **Tratamento de Erros**: Respostas HTTP apropriadas

---

## 📚 Documentação

- `README.md` - Documentação completa
- `QUICKSTART.md` - Guia de início rápido
- `example_usage.py` - Script de demonstração
- Código documentado com type hints

---

## 🎯 Próximos Passos (Melhorias Futuras)

- [ ] Renovação de empréstimos
- [ ] Reserva de livros
- [ ] Sistema de avaliações
- [ ] Notificações de atraso (email)
- [ ] Relatórios de uso
- [ ] Autenticação OAuth2
- [ ] Rate limiting
- [ ] Cache com Redis
- [ ] Publicação no Docker

---

**Status Final**: ✅ **CONCLUÍDO COM SUCESSO**

Todos os requisitos implementados e testados. API pronta para produção.

