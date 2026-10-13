# Arquitetura da API de Biblioteca

## Visão Geral

A API foi construída seguindo os princípios de Clean Code, separação de responsabilidades e best practices de desenvolvimento web. A arquitetura é organizada em camadas bem definidas.

## Estrutura em Camadas

```
┌─────────────────────────────────────────┐
│     Routers (API Endpoints)             │
├─────────────────────────────────────────┤
│  Dependencies (Middleware & Auth)       │
├─────────────────────────────────────────┤
│  Schemas (Pydantic - Validação)         │
├─────────────────────────────────────────┤
│  Models (SQLAlchemy - Banco de Dados)   │
├─────────────────────────────────────────┤
│  Core (Segurança, Config)               │
├─────────────────────────────────────────┤
│  Database (SQLAlchemy Session)          │
└─────────────────────────────────────────┘
```

## Componentes Principais

### 1. Core (`app/core/`)

#### `config.py`
- Configurações centralizadas da aplicação
- Constantes e variáveis de ambiente
- Parâmetros de negócio (LOAN_DAYS, MAX_LOANS_PER_USER, LATE_FEE_PER_DAY)

#### `security.py`
- Criptografia de senhas com bcrypt
- Geração e validação de JWT
- Funções de autenticação

**Funções principais:**
- `get_password_hash()`: Criptografa senha
- `verify_password()`: Valida senha
- `create_access_token()`: Gera JWT
- `decode_token()`: Decodifica e valida JWT

### 2. Database (`app/database.py`)

- Configuração SQLAlchemy
- Gerenciamento de sessões
- Factory de dependências para injeção

**Componentes:**
- `engine`: Engine SQLAlchemy para conexão
- `SessionLocal`: Factory de sessões
- `Base`: Classe base para modelos ORM
- `get_db()`: Dependency para injetar sessão nos endpoints

### 3. Models (`app/models.py`)

Define as tabelas do banco de dados usando SQLAlchemy ORM.

#### User
```
users
├── id (PK)
├── username (UNIQUE, INDEX)
├── email (UNIQUE, INDEX)
├── hashed_password
├── is_librarian
├── created_at
└── loans (relationship)
```

#### Book
```
books
├── id (PK)
├── title (INDEX)
├── author (INDEX)
├── isbn (UNIQUE, INDEX)
├── year
├── total_quantity
├── available_quantity
├── created_at
└── loans (relationship)
```

#### Loan
```
loans
├── id (PK)
├── user_id (FK → users)
├── book_id (FK → books)
├── loan_date
├── due_date
├── return_date (nullable)
├── fine
└── relationships (user, book)
```

### 4. Schemas (`app/schemas.py`)

Usa Pydantic para validação de entrada/saída.

**Validações automáticas:**
- Tipo de dado
- Formato de email
- Campos obrigatórios
- Conversão de tipos

**Schemas principais:**
- `UserCreate`: Validação de registro
- `BookCreate/Update`: CRUD de livros
- `LoanCreate/Return`: Empréstimos
- `TokenResponse`: Resposta de login

### 5. Dependencies (`app/dependencies.py`)

Injeção de dependências para autenticação.

**Dependências:**
- `get_current_user`: Extrai usuário do token JWT
- `get_current_librarian`: Valida se é bibliotecário

Usa FastAPI `Depends()` para injeção automática.

### 6. Routers (`app/routers/`)

Endpoints da API organizados por domínio.

#### auth.py
- `POST /api/auth/register`: Criar novo usuário
- `POST /api/auth/login`: Autenticação e geração de token

#### books.py
- `POST /api/books/`: Criar livro
- `GET /api/books/`: Listar todos
- `GET /api/books/{id}`: Detalhes
- `PUT /api/books/{id}`: Atualizar
- `DELETE /api/books/{id}`: Deletar
- `GET /api/books/search/by-title`: Buscar por título
- `GET /api/books/search/by-author`: Buscar por autor

#### loans.py
- `POST /api/loans/`: Criar empréstimo
- `GET /api/loans/`: Listar todos (bibliotecário)
- `GET /api/loans/my-loans`: Meus empréstimos
- `GET /api/loans/active-loans/{user_id}`: Ativos de usuário
- `GET /api/loans/{id}`: Detalhes
- `POST /api/loans/{id}/return`: Devolver livro

## Fluxo de Autenticação

```
1. POST /api/auth/login (username, password)
   ↓
2. Validar credenciais no banco
   ↓
3. Gerar JWT com user_id no payload
   ↓
4. Retornar token (válido por 30 min padrão)
   ↓
5. Cliente envia: Authorization: Bearer <token>
   ↓
6. Middleware valida JWT
   ↓
7. Extrai user_id do payload
   ↓
8. Carrega usuário do banco
   ↓
9. Injeta User objeto no handler
```

## Fluxo de Empréstimo

```
POST /api/loans/
   ↓
Validar token (get_current_user)
   ↓
Validar limite (max 3 ativos)
   ↓
Validar livro existe
   ↓
Validar exemplares disponíveis
   ↓
Calcular due_date (hoje + 14 dias)
   ↓
Criar registro Loan
   ↓
Decrementar available_quantity
   ↓
Salvar no banco
   ↓
Retornar dados do empréstimo
```

## Fluxo de Devolução

```
POST /api/loans/{id}/return
   ↓
Validar token
   ↓
Carregar empréstimo
   ↓
Validar se já foi devolvido
   ↓
Validar permissões (próprio ou bibliotecário)
   ↓
Calcular fine (se há atraso)
   ↓
Atualizar return_date e fine
   ↓
Incrementar available_quantity
   ↓
Salvar no banco
   ↓
Retornar empréstimo atualizado
```

## Validações de Negócio

### Autenticação
- ✅ Username não pode ser duplicado
- ✅ Email não pode ser duplicado
- ✅ Senha mínimo 1 caractere (ajuste conforme necessário)
- ✅ Email deve ser válido

### Livros
- ✅ ISBN deve ser único
- ✅ Apenas bibliotecário pode criar/atualizar/deletar
- ✅ Quantidade total deve ser > 0

### Empréstimos
- ✅ Leitor não pode ter > 3 empréstimos simultâneos
- ✅ Livro deve ter exemplar disponível
- ✅ Cada livro só pode ser devolvido uma vez
- ✅ Multa é calculada automaticamente por dia de atraso

## Segurança

### Proteção de Senhas
- Bcrypt com salt automático
- Senhas nunca armazenadas em plain text
- Verificação em tempo de login

### JWT
- Secret key configurável
- Expiração automática (30 min)
- Validação de assinatura
- Payload contém apenas user_id

### Controle de Acesso
- Role-based (bibliotecário vs leitor)
- Permissões em endpoint específico
- Validação de propriedade (próprio empréstimo)

### Entrada
- Validação com Pydantic
- Type hints em todos os modelos
- Rejeição de campos extras

## Performance

### Índices no Banco
- PK em todas as tabelas
- INDEX em username, email (users)
- INDEX em title, author (books)
- FK automaticamente indexadas

### Queries Eficientes
- Uso de filter() com indexed columns
- Lazy loading de relationships (quando necessário)
- Limit/offset para paginação

### CORS
- Habilitado para desenvolvimento
- Ajuste em produção conforme necessário

## Tratamento de Erros

### HTTP Status Codes
- `200`: Sucesso (GET, PUT)
- `201`: Criado (POST)
- `204`: Deletado (DELETE)
- `400`: Validação ou regra de negócio
- `401`: Não autenticado
- `403`: Sem permissão
- `404`: Não encontrado
- `500`: Erro interno

### Mensagens de Erro
- Descritivas em português
- Indicam problema específico
- Não expõem detalhes técnicos

## Testing

### Estratégia
- Unit tests para regras de negócio
- Integration tests para fluxos
- Fixtures para dados de teste
- Banco de dados temporário (test.db)

### Cobertura
- Autenticação (registro, login)
- CRUD de livros
- Empréstimos (criar, devolver, limites)
- Validações e erros
- Controle de acesso

### Rodar Testes
```bash
pytest              # Todos
pytest -v           # Verbose
pytest --cov        # Com cobertura
pytest tests/test_auth.py  # Específico
```

## Deploy e Produção

### Checklist Pre-Deploy
- [ ] Alterar SECRET_KEY para valor seguro
- [ ] Desabilitar CORS ou configurar origins
- [ ] Usar banco PostgreSQL (não SQLite)
- [ ] Configurar variáveis de ambiente
- [ ] Rodar testes completos
- [ ] Validar documentação Swagger

### Variáveis de Ambiente
```bash
SECRET_KEY=seu-valor-seguro
DATABASE_URL=postgresql://user:pass@host/db
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Servidor
```bash
# Desenvolvimento
uvicorn main:app --reload

# Produção
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Extensões Futuras

### Curto Prazo
- Rate limiting por IP
- Validação mais forte de senha
- Email confirmation

### Médio Prazo
- Sistema de reservas de livros
- Histórico de empréstimos/leitura
- Recomendações personalizadas

### Longo Prazo
- Sistema de pagamento para multas
- Notificações por email
- Dashboard administrativo
- Integração com sistema de catálogo
- Mobile app com sincronização

## Monitoramento

### Logs (Sugerido adicionar)
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### Métricas (Sugerido adicionar)
- Tempo de resposta
- Erros por endpoint
- Taxa de sucesso de login
- Livros mais emprestados

### Alertas
- Muitos erros 401/403
- Atraso sistemático nas devoluções
- Base de dados indisponível
