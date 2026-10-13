# Arquitetura - Library API

## Visão Geral

A Library API é construída com uma arquitetura em camadas seguindo os princípios de Clean Code e SOLID:

```
┌─────────────────────────────────────────────────────────┐
│                   API Routes Layer                       │
│            (Endpoints HTTP / Controllers)                │
├─────────────────────────────────────────────────────────┤
│                   Business Logic Layer                   │
│            (CRUD Operations / Services)                  │
├─────────────────────────────────────────────────────────┤
│                   Data Access Layer                      │
│            (SQLAlchemy ORM / Models)                     │
├─────────────────────────────────────────────────────────┤
│                   Database Layer                         │
│            (SQLite Database)                             │
└─────────────────────────────────────────────────────────┘
```

## Estrutura de Diretórios

### `/app/routes/` - Layer de Rotas
Define os endpoints HTTP da aplicação. Cada arquivo representa um domínio:
- `auth.py` - Autenticação e registro de usuários
- `books.py` - CRUD de livros
- `loans.py` - Empréstimos e devoluções

**Responsabilidades:**
- Receber requisições HTTP
- Validar autenticação/autorização
- Chamar CRUD operations
- Retornar respostas HTTP

### `/app/crud/` - Layer de Negócio
Implementa operações de banco de dados (Create, Read, Update, Delete).

**Arquivo por entidade:**
- `user.py` - Operações de usuário
- `book.py` - Operações de livro
- `loan.py` - Operações de empréstimo

**Responsabilidades:**
- Lógica de negócio (validações, cálculos)
- Operações com banco de dados
- Transações

### `/app/models/` - Layer de Dados
Define as entidades/modelos usando SQLAlchemy ORM.

- `user.py` - Modelo User (email, senha, role)
- `book.py` - Modelo Book (title, author, ISBN, quantidade)
- `loan.py` - Modelo Loan (relação entre Reader e Book)

**Responsabilidades:**
- Definir estrutura do banco
- Validações ao nível do banco
- Relacionamentos

### `/app/schemas/` - Layer de Validação
Define os schemas de entrada/saída usando Pydantic.

- `user.py` - Schemas de usuário (UserRegister, UserLogin)
- `book.py` - Schemas de livro (BookCreate, BookUpdate)
- `loan.py` - Schemas de empréstimo (LoanCreate, LoanReturn)

**Responsabilidades:**
- Validar dados de entrada
- Serializar dados de saída
- Documentação automática

### `/app/database.py` - Configuração de Banco
- Cria a engine SQLAlchemy
- Define a session factory
- Estabelece conexão SQLite

### `/app/security.py` - Camada de Segurança
- Hash de senhas com bcrypt
- Geração de JWT
- Validação de tokens

### `/tests/` - Testes Unitários
- `test_auth.py` - Testes de autenticação (6 testes)
- `test_books.py` - Testes de livros (11 testes)
- `test_loans.py` - Testes de empréstimos (13 testes)
- `conftest.py` - Fixtures e configuração

## Fluxo de Requisição

### Exemplo: Emprestar um livro

```
1. POST /loans/ → app/routes/loans.py::borrow_book()
   ↓
2. Valida autenticação (security.py::verify_token)
   ↓
3. Verifica autorização (apenas readers podem emprestar)
   ↓
4. Valida limite de 3 empréstimos (crud/loan.py::get_loans_count)
   ↓
5. Cria empréstimo (crud/loan.py::create_loan)
   - Verifica disponibilidade do livro
   - Diminui quantidade disponível
   - Define data de devolução (14 dias)
   ↓
6. Retorna Loan (schemas/loan.py::LoanResponse)
   ↓
7. Cliente recebe JSON com dados do empréstimo
```

## Padrões Utilizados

### 1. Dependency Injection
FastAPI resolve automaticamente dependências:
```python
def create_book(
    book: BookCreate,
    token: dict = Depends(verify_token),  # Injeção de token
    db: Session = Depends(get_db)         # Injeção de sessão
)
```

### 2. Validação em Camadas
```
HTTP → Pydantic (schemas) → SQLAlchemy (models) → Business Logic
```

### 3. Separação de Responsabilidades
- **Routes**: Protocolo HTTP
- **CRUD**: Lógica de dados
- **Models**: Estrutura
- **Security**: Autenticação
- **Database**: Conexão

### 4. Type Hints
Código type-safe em Python 3.9+:
```python
def get_user_by_id(db: Session, user_id: int) -> User:
    ...
```

## Fluxo de Autenticação

```
1. Registro
   POST /auth/register → criar usuário → salvar senha hash
   
2. Login
   POST /auth/login → verificar credenciais → gerar JWT
   
3. Requisição Autenticada
   GET /books/
   Header: Authorization: Bearer {jwt_token}
   
4. Validação
   security.py::verify_token() → decodifica JWT → retorna user_id
   
5. Autorização
   verify_librarian() → verifica role do usuário
```

## Camadas de Segurança

### 1. Autenticação (JWT)
- Token com expiração de 30 minutos
- Secret key para assinatura
- Validação em cada requisição protegida

### 2. Autorização (Role-based)
- Bibliotecário: Gerencia livros
- Leitor: Empresta e devolve livros

### 3. Validação de Entrada
- Pydantic valida tipos
- Validações customizadas nos schemas
- Validações de negócio no CRUD

### 4. Proteção de Dados
- Senhas hasheadas com bcrypt
- SQLAlchemy protege contra SQL injection
- CORS configurado

## Entidades e Relacionamentos

```
User
├── id (PK)
├── email (unique)
├── full_name
├── hashed_password
├── role (librarian | reader)
└── is_active

Book
├── id (PK)
├── title
├── author
├── isbn (unique)
├── year
├── total_quantity
└── available_quantity

Loan
├── id (PK)
├── book_id (FK → Book.id)
├── reader_id (FK → User.id)
├── loan_date
├── due_date
├── return_date (nullable)
└── fine
```

## Tratamento de Erros

A API retorna erros HTTP padrão:

```python
# 400 Bad Request - Validação ou regra de negócio violada
if book.available_quantity <= 0:
    raise HTTPException(status_code=400, detail="No copies available")

# 401 Unauthorized - Token inválido/expirado
if not token:
    raise HTTPException(status_code=401, detail="Could not validate credentials")

# 403 Forbidden - Sem permissão
if user.role != "librarian":
    raise HTTPException(status_code=403, detail="Only librarians can manage books")

# 404 Not Found - Recurso não existe
if not book:
    raise HTTPException(status_code=404, detail="Book not found")
```

## Configuração do Banco de Dados

### SQLite
- Arquivo local: `library.db`
- Criado automaticamente ao iniciar
- Sem dependências externas
- Ideal para desenvolvimento/testes

### Migração para Produção
Para usar PostgreSQL/MySQL:
1. Instalar driver apropriado (psycopg2, mysql-connector)
2. Alterar DATABASE_URL em `app/database.py`
3. O resto do código funciona sem mudanças (benefício do ORM)

## Testes

### Estratégia de Teste
- **Unit Tests**: CRUD operations isoladas
- **Integration Tests**: Fluxos completos HTTP
- **Fixtures**: Setup de dados (conftest.py)

### Cobertura
- Autenticação: 6 testes
- Livros (CRUD): 11 testes
- Empréstimos (negócio complexo): 13 testes
- Total: 30 testes passando

### Executar com Coverage
```bash
pytest --cov=app tests/
```

## Performance

### Otimizações Implementadas
1. **Database Indexes**: ISBN, email, title/author
2. **Query Filtering**: Retorna apenas ativos
3. **Paginação**: Limite de 10 por página
4. **Lazy Loading**: Relations carregadas sob demanda

### Escalabilidade
- SQLite para desenvolvimento
- PostgreSQL para produção
- Cache (Redis) pode ser adicionado
- API stateless (scale horizontalmente)
