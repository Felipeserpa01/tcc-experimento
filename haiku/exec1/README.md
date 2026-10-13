# API de Gerenciamento de Biblioteca

Uma API REST completa desenvolvida com FastAPI para gerenciar uma biblioteca digital, incluindo autenticação de usuários, gerenciamento de livros e controle de empréstimos.

## Características

- ✅ Autenticação JWT com dois tipos de usuário (bibliotecário e leitor)
- ✅ Senhas armazenadas de forma segura com bcrypt
- ✅ CRUD completo para livros
- ✅ Sistema de empréstimos com limite de 3 livros por leitor
- ✅ Cálculo automático de multas por atraso
- ✅ Busca de livros por título e autor
- ✅ Validação de entrada com Pydantic
- ✅ Testes unitários abrangentes com pytest
- ✅ Documentação interativa (Swagger UI)

## Estrutura do Projeto

```
.
├── app/
│   ├── core/
│   │   ├── config.py          # Configurações da aplicação
│   │   └── security.py        # JWT e hash de senhas
│   ├── routers/
│   │   ├── auth.py            # Endpoints de autenticação
│   │   ├── books.py           # Endpoints de livros
│   │   └── loans.py           # Endpoints de empréstimos
│   ├── database.py            # Configuração SQLAlchemy
│   ├── models.py              # Modelos do banco de dados
│   ├── schemas.py             # Schemas Pydantic
│   ├── dependencies.py        # Dependências FastAPI
│   └── __init__.py
├── tests/
│   ├── test_auth.py           # Testes de autenticação
│   ├── test_books.py          # Testes de livros
│   ├── test_loans.py          # Testes de empréstimos
│   ├── conftest.py            # Fixtures do pytest
│   └── __init__.py
├── main.py                    # Aplicação FastAPI
├── requirements.txt           # Dependências
├── pytest.ini                 # Configuração pytest
└── README.md                  # Este arquivo
```

## Instalação

### Pré-requisitos
- Python 3.8+
- pip

### Passos

1. Clone ou extraia o projeto:
```bash
cd /Users/felipeserpa/Desktop/tcc-experimento/haiku/exec1
```

2. Crie um ambiente virtual (opcional, mas recomendado):
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Executando a Aplicação

```bash
uvicorn main:app --reload
```

A API estará disponível em `http://localhost:8000`

### Documentação Interativa
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Executando os Testes

```bash
# Executar todos os testes
pytest

# Com cobertura
pytest --cov=app

# Verbose
pytest -v

# Teste específico
pytest tests/test_auth.py -v
```

## Endpoints da API

### Autenticação

**POST** `/api/auth/register`
- Registrar um novo usuário
```json
{
  "username": "string",
  "email": "user@example.com",
  "password": "string",
  "is_librarian": false
}
```

**POST** `/api/auth/login`
- Fazer login e obter token JWT
```json
{
  "username": "string",
  "password": "string"
}
```

### Livros

**POST** `/api/books/` (Apenas bibliotecário)
- Criar um novo livro

**GET** `/api/books/`
- Listar todos os livros

**GET** `/api/books/{book_id}`
- Obter detalhes de um livro

**PUT** `/api/books/{book_id}` (Apenas bibliotecário)
- Atualizar um livro

**DELETE** `/api/books/{book_id}` (Apenas bibliotecário)
- Deletar um livro

**GET** `/api/books/search/by-title?title=query`
- Buscar livros por título

**GET** `/api/books/search/by-author?author=query`
- Buscar livros por autor

### Empréstimos

**POST** `/api/loans/`
- Registrar um novo empréstimo

**GET** `/api/loans/`
- Listar todos os empréstimos (Apenas bibliotecário)

**GET** `/api/loans/my-loans`
- Listar meus empréstimos ativos

**GET** `/api/loans/active-loans/{user_id}`
- Listar empréstimos ativos de um usuário

**GET** `/api/loans/{loan_id}`
- Obter detalhes de um empréstimo

**POST** `/api/loans/{loan_id}/return`
- Registrar a devolução de um livro
```json
{
  "return_date": "2024-09-20T10:30:00Z"
}
```

## Autenticação

Todos os endpoints (exceto login e register) requerem um token JWT no header `Authorization`:

```bash
Authorization: Bearer <seu_token_jwt>
```

## Modelos de Dados

### User
- `id`: Identificador único
- `username`: Nome de usuário único
- `email`: Email único
- `hashed_password`: Senha criptografada
- `is_librarian`: Tipo de usuário
- `created_at`: Data de criação

### Book
- `id`: Identificador único
- `title`: Título do livro
- `author`: Autor
- `isbn`: ISBN único
- `year`: Ano de publicação
- `total_quantity`: Quantidade total
- `available_quantity`: Quantidade disponível
- `created_at`: Data de criação

### Loan
- `id`: Identificador único
- `user_id`: ID do usuário (leitor)
- `book_id`: ID do livro
- `loan_date`: Data do empréstimo
- `due_date`: Data de devolução prevista
- `return_date`: Data de devolução real (null se não devolvido)
- `fine`: Multa por atraso

## Regras de Negócio

1. **Limite de empréstimos**: Cada leitor pode ter no máximo 3 empréstimos simultâneos
2. **Disponibilidade**: Um livro só pode ser emprestado se houver exemplares disponíveis
3. **Período de empréstimo**: O padrão é 14 dias
4. **Multa**: R$ 5,00 por dia de atraso
5. **Usuários**: Apenas bibliotecários podem criar, atualizar e deletar livros

## Configuração

Edite `app/core/config.py` para ajustar:
- `SECRET_KEY`: Chave secreta para JWT
- `LOAN_DAYS`: Dias de empréstimo (padrão: 14)
- `LATE_FEE_PER_DAY`: Multa diária em R$ (padrão: 5.0)
- `MAX_LOANS_PER_USER`: Máximo de empréstimos simultâneos (padrão: 3)

## Banco de Dados

A aplicação usa SQLite por padrão. O arquivo `biblioteca.db` será criado automaticamente ao iniciar.

Para usar outro banco de dados, altere `DATABASE_URL` em `app/core/config.py`:
- PostgreSQL: `postgresql://user:password@localhost/dbname`
- MySQL: `mysql://user:password@localhost/dbname`

## Exemplo de Uso Completo

```bash
# 1. Registrar um novo leitor
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "joao",
    "email": "joao@example.com",
    "password": "senha123",
    "is_librarian": false
  }'

# 2. Fazer login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "joao",
    "password": "senha123"
  }'

# 3. Com o token obtido, emprestar um livro
TOKEN="seu_token_aqui"
curl -X POST http://localhost:8000/api/loans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 1
  }'

# 4. Devolver o livro
curl -X POST http://localhost:8000/api/loans/1/return \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "return_date": "2024-09-20T10:30:00Z"
  }'
```

## Tratamento de Erros

A API retorna respostas de erro padronizadas:

```json
{
  "detail": "Descrição do erro"
}
```

Códigos HTTP utilizados:
- `200`: Sucesso
- `201`: Criado com sucesso
- `204`: Sem conteúdo (deleção bem-sucedida)
- `400`: Requisição inválida
- `401`: Não autenticado
- `403`: Sem permissão
- `404`: Não encontrado
- `500`: Erro interno do servidor

## Testes

O projeto inclui testes abrangentes para todos os principais fluxos:

- Autenticação (registro, login)
- Gerenciamento de livros (CRUD, busca)
- Gerenciamento de empréstimos (emprestar, devolver, multas)
- Validações e limites
- Controle de acesso (bibliotecário vs leitor)

Execute `pytest -v` para ver todos os testes rodando.

## Segurança

- Senhas são criptografadas com bcrypt
- JWT para autenticação stateless
- CORS habilitado para desenvolvimento
- Validação de entrada com Pydantic
- Separação de responsabilidades por usuário (bibliotecário/leitor)

## Melhorias Futuras

- [ ] Rate limiting
- [ ] Email notifications
- [ ] Sistema de reservas
- [ ] Histórico de empréstimos
- [ ] Multas online
- [ ] Renovação de empréstimos
- [ ] Recomendações de livros
- [ ] Dashboard administrativo
- [ ] Integração com sistema de pagamento
- [ ] Backup e restauração de dados

## Licença

Este projeto é fornecido como exemplo educacional.

## Suporte

Para dúvidas ou problemas, verifique:
1. A documentação Swagger em `/docs`
2. Os testes em `tests/`
3. As configurações em `app/core/config.py`
