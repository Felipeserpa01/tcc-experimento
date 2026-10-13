# Estrutura do Projeto

## Árvore de Diretórios

```
library-api/
├── app/                          # Código principal da aplicação
│   ├── __init__.py
│   ├── main.py                  # Aplicação FastAPI principal
│   ├── database.py              # Configuração SQLAlchemy
│   ├── security.py              # Autenticação JWT e hash de senha
│   │
│   ├── models/                  # Modelos SQLAlchemy (ORM)
│   │   ├── __init__.py
│   │   ├── user.py              # Modelo User (autenticação)
│   │   ├── book.py              # Modelo Book (acervo)
│   │   └── loan.py              # Modelo Loan (empréstimos)
│   │
│   ├── schemas/                 # Schemas Pydantic (validação)
│   │   ├── __init__.py
│   │   ├── user.py              # UserRegister, UserLogin, UserResponse
│   │   ├── book.py              # BookCreate, BookUpdate, BookResponse
│   │   └── loan.py              # LoanCreate, LoanReturn, LoanResponse
│   │
│   ├── crud/                    # Operações de banco de dados
│   │   ├── __init__.py
│   │   ├── user.py              # get_user, create_user, etc
│   │   ├── book.py              # CRUD completo de livros
│   │   └── loan.py              # Criar, listar, devolver empréstimos
│   │
│   └── routes/                  # Endpoints HTTP (Controllers)
│       ├── __init__.py
│       ├── auth.py              # POST /auth/register, /auth/login
│       ├── books.py             # POST/GET/PUT/DELETE /books/
│       └── loans.py             # POST /loans/, GET /loans/, POST /loans/{id}/return
│
├── tests/                       # Testes unitários e de integração
│   ├── __init__.py
│   ├── conftest.py              # Fixtures pytest (setup de testes)
│   ├── test_auth.py             # 6 testes de autenticação
│   ├── test_books.py            # 11 testes de CRUD de livros
│   └── test_loans.py            # 13 testes de empréstimos
│
├── requirements.txt             # Dependências Python
├── run.sh                       # Scripts de utilidade
│
├── README.md                    # Documentação principal
├── ARCHITECTURE.md              # Arquitetura técnica
├── EXAMPLES.md                  # Exemplos de requisições HTTP
├── REQUIREMENTS.md              # Detalhes sobre dependências
├── PROJECT_STRUCTURE.md         # Este arquivo
│
└── .env.example                 # Template de variáveis de ambiente
    .gitignore                  # Arquivos ignorados pelo git
```

## Arquivos Chave

### Configuração
- **requirements.txt**: Lista de todas as dependências
- **.env.example**: Template de configuração
- **run.sh**: Scripts para instalar, executar e testar

### Documentação
- **README.md**: Guia de uso e instalação
- **ARCHITECTURE.md**: Design técnico da aplicação
- **EXAMPLES.md**: Exemplos com curl/Postman
- **REQUIREMENTS.md**: Informações sobre cada dependência

### Código Principal
- **app/main.py**: Inicializa FastAPI e inclui rotas
- **app/database.py**: Configuração do SQLite
- **app/security.py**: JWT e criptografia de senhas

## Mapeamento de Funcionalidades

### Autenticação (`/auth`)
```
Arquivo: app/routes/auth.py
├── POST /register → criar novo usuário
└── POST /login    → gerar JWT token
```

### Gerenciamento de Livros (`/books`)
```
Arquivo: app/routes/books.py
├── POST   /           → criar livro (bibliotecário)
├── GET    /           → listar livros
├── GET    /search?q=  → buscar por título/autor
├── GET    /{id}       → detalhes do livro
├── PUT    /{id}       → atualizar livro (bibliotecário)
└── DELETE /{id}       → deletar livro (bibliotecário)
```

### Empréstimos (`/loans`)
```
Arquivo: app/routes/loans.py
├── POST   /           → emprestar livro (leitor)
├── GET    /           → listar empréstimos ativos (leitor)
└── POST   /{id}/return → devolver livro
```

## Padrão de Requisição

Cada requisição segue este fluxo:

```
1. HTTP Request
   ↓
2. routes/ (valida HTTP)
   ↓
3. security.py (valida autenticação)
   ↓
4. crud/ (valida regras de negócio)
   ↓
5. models/ (persiste no banco)
   ↓
6. schemas/ (serializa resposta)
   ↓
7. HTTP Response
```

## Testes

### Cobertura de Testes
```
test_auth.py    → 6 testes
├── Registro de usuários
├── Login (válido/inválido)
└── Validações de email/role

test_books.py   → 11 testes
├── CRUD completo
├── Busca e paginação
└── Validações (ISBN duplicado)

test_loans.py   → 13 testes
├── Criar empréstimos
├── Validações (cópias disponíveis, limite 3)
├── Devolver livros
└── Cálculo de multas

Total: 30 testes ✅
```

## Banco de Dados

### Tabelas
```
users (autenticação)
├── id (PK)
├── email (unique)
├── full_name
├── hashed_password
├── role (enum: librarian | reader)
└── is_active

books (acervo)
├── id (PK)
├── title
├── author
├── isbn (unique, index)
├── year
├── total_quantity
└── available_quantity

loans (empréstimos)
├── id (PK)
├── book_id (FK)
├── reader_id (FK)
├── loan_date
├── due_date
├── return_date (nullable)
└── fine (multa por atraso)
```

### Índices
- users.email
- books.isbn
- books.title
- books.author

## Variáveis de Ambiente

```env
DATABASE_URL=sqlite:///./library.db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
API_PORT=8000
```

## Comandos Principais

```bash
# Instalar dependências
./run.sh install

# Rodar servidor
./run.sh run

# Executar testes
./run.sh test

# Gerar relatório de cobertura
./run.sh test-coverage

# Limpar arquivos temporários
./run.sh clean

# Resetar banco de dados
./run.sh reset
```

## Estatísticas do Projeto

| Métrica | Valor |
|---------|-------|
| Linhas de código (app) | ~1000 |
| Linhas de testes | ~500 |
| Testes passando | 30/30 ✅ |
| Endpoints | 13 |
| Tabelas do DB | 3 |
| Dependências | 11 |
| Tempo de execução de testes | ~20s |

## Próximos Passos

### Possíveis Melhorias
1. **Cache** - Redis para melhorar performance
2. **Autenticação Social** - Google, GitHub OAuth
3. **Notificações** - Email para multas/devoluções
4. **Relatórios** - Livros mais emprestados, leitores ativos
5. **UI** - Frontend React/Vue
6. **Documentação** - OpenAPI Schema customizado
7. **Logging** - Registrar todas as operações
8. **Backup** - Automático do banco de dados

### Deploy
1. **Docker** - Containerizar a aplicação
2. **CI/CD** - GitHub Actions para testes automáticos
3. **Database** - Migrar para PostgreSQL
4. **Hosting** - Heroku, AWS, DigitalOcean, etc

## Contato e Suporte

Para dúvidas ou sugestões, abra uma issue no repositório.
