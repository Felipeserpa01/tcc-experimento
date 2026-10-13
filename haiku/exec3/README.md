# Biblioteca API

API REST completa para gerenciamento de biblioteca desenvolvida com Python e FastAPI.

## Estrutura do Projeto

```
biblioteca/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Aplicação principal
│   ├── database.py             # Configuração do banco de dados
│   ├── config.py               # Configurações gerais
│   ├── models/                 # Modelos SQLAlchemy
│   │   ├── user.py
│   │   ├── book.py
│   │   └── loan.py
│   ├── schemas/                # Validação com Pydantic
│   │   ├── user.py
│   │   ├── book.py
│   │   └── loan.py
│   ├── routes/                 # Rotas da API
│   │   ├── auth.py
│   │   ├── books.py
│   │   └── loans.py
│   ├── security/               # Autenticação JWT
│   │   └── jwt.py
│   └── utils/                  # Utilitários
│       └── validators.py
├── tests/                      # Testes unitários
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_books.py
│   └── test_loans.py
├── requirements.txt
└── README.md
```

## Funcionalidades

### 1. Autenticação e Usuários
- ✅ Registro de usuários com validação de senha forte
- ✅ Login com JWT (Access Token + Refresh Token)
- ✅ Dois tipos de usuário: Bibliotecário e Leitor
- ✅ Senhas criptografadas com bcrypt

### 2. Gerenciamento de Livros (CRUD)
- ✅ Criar livros (apenas bibliotecários)
- ✅ Listar todos os livros
- ✅ Buscar por título ou autor
- ✅ Atualizar informações de livros (apenas bibliotecários)
- ✅ Deletar livros (apenas bibliotecários)
- ✅ Controle de quantidade disponível

### 3. Gerenciamento de Empréstimos
- ✅ Registrar empréstimo de livro
- ✅ Verificar disponibilidade antes de emprestar
- ✅ Limitar a 3 empréstimos simultâneos por leitor
- ✅ Registrar devolução de livro
- ✅ Calcular multa por atraso (5.0 por dia)
- ✅ Listar empréstimos ativos do leitor

### 4. Requisitos Gerais
- ✅ Banco de dados SQLite
- ✅ Validação robusta de dados
- ✅ Tratamento de erros com status HTTP apropriados
- ✅ Testes unitários com pytest
- ✅ Documentação automática (Swagger)

## Instalação

### Pré-requisitos
- Python 3.10+
- pip

### Passos

1. Clone o repositório (ou crie a estrutura)
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Rode a aplicação:
```bash
uvicorn app.main:app --reload
```

A API estará disponível em `http://localhost:8000`

### Documentação
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Como Usar

### Registrar um Usuário

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "joao_silva",
    "email": "joao@example.com",
    "password": "Senha123",
    "user_type": "reader"
  }'
```

### Fazer Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "joao_silva",
    "password": "Senha123"
  }'
```

Resposta:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Criar Livro (Bibliotecário)

```bash
curl -X POST "http://localhost:8000/books/" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "isbn": "978-0132350884",
    "year": 2008,
    "total_quantity": 5,
    "description": "A handbook of agile software craftsmanship"
  }'
```

### Buscar Livros

```bash
# Por título
curl "http://localhost:8000/books/search?title=Clean"

# Por autor
curl "http://localhost:8000/books/search?author=Robert"
```

### Emprestar um Livro

```bash
curl -X POST "http://localhost:8000/loans/" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 1}'
```

### Listar Empréstimos Ativos

```bash
curl -X GET "http://localhost:8000/loans/user/active" \
  -H "Authorization: Bearer {access_token}"
```

### Devolver um Livro

```bash
curl -X POST "http://localhost:8000/loans/return" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"loan_id": 1}'
```

## Testes

Execute os testes com pytest:

```bash
pytest tests/ -v
```

Para ver a cobertura de testes:

```bash
pytest tests/ --cov=app --cov-report=html
```

## Validações Implementadas

### Usuários
- **Username**: 3-50 caracteres, apenas letras, números, hífen e underscore
- **Senha**: Mínimo 8 caracteres, deve conter maiúsculas, minúsculas e números
- **Email**: Formato válido de email

### Livros
- **ISBN**: Formato válido (10 ou 13 dígitos)
- **Ano**: Entre 1000 e 2100
- **Quantidade**: Não negativa

### Empréstimos
- **Disponibilidade**: Não permite emprestar se não há cópias disponíveis
- **Limite**: Máximo 3 empréstimos ativos por leitor
- **Multa**: Calculada em R$ 5,00 por dia de atraso

## Erros Comuns

### 401 - Unauthorized
- Token inválido ou expirado
- Solução: Faça login novamente

### 403 - Forbidden
- Usuário não tem permissão
- Solução: Apenas bibliotecários podem criar/editar/deletar livros

### 400 - Bad Request
- Dados inválidos
- Solução: Verifique o formato dos dados enviados

### 404 - Not Found
- Recurso não encontrado
- Solução: Verifique se o ID está correto

## Configurações

As configurações podem ser alteradas em `app/config.py`:

```python
MAX_LOANS_PER_USER = 3              # Máximo de empréstimos
LOAN_DURATION_DAYS = 14             # Dias até vencimento
LATE_FINE_PER_DAY = 5.0            # Multa diária em reais
```

## Segurança

- Senhas são criptografadas com bcrypt
- Autenticação via JWT com tokens com expiração
- Validação de entrada em todos os endpoints
- Proteção CORS configurada
- Senhas fortes obrigatórias

## Melhorias Futuras

- [ ] Renovação de empréstimos
- [ ] Reserva de livros
- [ ] Sistema de avaliações
- [ ] Notificações de atraso
- [ ] Relatórios de uso
- [ ] Autenticação OAuth2
- [ ] Rate limiting
- [ ] Cache de dados

## Contribuição

Sinta-se livre para contribuir com melhorias e correções.

## Licença

Este projeto é de código aberto e pode ser utilizado livremente.
