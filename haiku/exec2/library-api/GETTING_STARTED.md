# Começando Rápido - Library API

## 5 Minutos para Começar

### 1. Instalar (1 minuto)
```bash
cd library-api
pip install -r requirements.txt
```

### 2. Iniciar Servidor (1 minuto)
```bash
python3 -m uvicorn app.main:app --reload
```

Acesse: http://localhost:8000/docs (Documentação interativa)

### 3. Registrar Usuário (1 minuto)
```bash
# No Swagger UI ou:
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "full_name": "John Doe",
    "password": "password123",
    "role": "reader"
  }'
```

### 4. Fazer Login (1 minuto)
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'

# Salve o access_token retornado
TOKEN="seu_token_aqui"
```

### 5. Usar a API (1 minuto)
```bash
# Listar livros
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/books/
```

## Rotas Principais

### 🔐 Autenticação
- `POST /auth/register` - Criar conta
- `POST /auth/login` - Fazer login

### 📚 Livros
- `POST /books/` - Criar livro (bibliotecário)
- `GET /books/` - Listar livros
- `GET /books/search?q=python` - Buscar livros
- `GET /books/{id}` - Detalhes
- `PUT /books/{id}` - Atualizar (bibliotecário)
- `DELETE /books/{id}` - Deletar (bibliotecário)

### 📖 Empréstimos
- `POST /loans/` - Emprestar livro (leitor)
- `GET /loans/` - Meus empréstimos
- `POST /loans/{id}/return` - Devolver livro

## Usuários de Teste

### Bibliotecário
```json
{
  "email": "librarian@test.com",
  "full_name": "Library Admin",
  "password": "admin123",
  "role": "librarian"
}
```

### Leitor
```json
{
  "email": "reader@test.com",
  "full_name": "John Reader",
  "password": "reader123",
  "role": "reader"
}
```

## Executar Testes

```bash
# Todos os testes (30 no total)
python3 -m pytest tests/ -v

# Com cobertura
python3 -m pytest tests/ --cov=app

# Testes rápidos
python3 -m pytest tests/ -q
```

## Usar Scripts Auxiliares

```bash
# Instalar
./run.sh install

# Rodar servidor
./run.sh run

# Testes
./run.sh test

# Testes com cobertura
./run.sh test-coverage

# Limpar
./run.sh clean

# Resetar banco
./run.sh reset
```

## Estrutura Rápida

```
app/
├── routes/        → Endpoints HTTP
├── crud/          → Lógica de negócio
├── models/        → Estrutura do BD
├── schemas/       → Validação de dados
├── database.py    → Conexão BD
├── security.py    → Autenticação
└── main.py        → Aplicação principal

tests/
├── test_auth.py   → Testes de autenticação
├── test_books.py  → Testes de livros
├── test_loans.py  → Testes de empréstimos
└── conftest.py    → Setup de testes
```

## Funcionalidades Implementadas ✅

- ✅ Autenticação JWT
- ✅ Registro e Login
- ✅ Dois tipos de usuário (Bibliotecário e Leitor)
- ✅ Senhas seguras (bcrypt)
- ✅ CRUD completo de livros
- ✅ Busca de livros
- ✅ Sistema de empréstimos
- ✅ Limite de 3 empréstimos por leitor
- ✅ Devoluções com cálculo de multa
- ✅ 30 testes unitários
- ✅ Validação de entrada
- ✅ Tratamento de erros
- ✅ Documentação automática (Swagger)

## Regras de Negócio

### Empréstimos
- Duração: 14 dias
- Limite por leitor: 3 livros simultâneos
- Multa por atraso: R$ 5,00 por dia

### Usuários
- **Bibliotecário**: Gerencia livros
- **Leitor**: Empresta e devolve livros

### Livros
- ISBN deve ser único
- Quantidade disponível não pode ser negativa

## Documentação Completa

- 📖 **README.md** - Guia principal e instalação
- 🏗️ **ARCHITECTURE.md** - Design técnico
- 📋 **PROJECT_STRUCTURE.md** - Estrutura de pastas
- 💻 **EXAMPLES.md** - Exemplos de requisições
- 📦 **REQUIREMENTS.md** - Detalhes de dependências

## Troubleshooting

### Porta 8000 em uso?
```bash
python3 -m uvicorn app.main:app --reload --port 8001
```

### "No module named app"?
```bash
# Certifique-se que está no diretório correto
cd library-api
# Ative o virtual env
source venv/bin/activate
```

### Testes falhando?
```bash
# Resetar banco de testes
rm test.db
# Rodar novamente
pytest tests/ -v
```

## Next Steps

1. Explore a documentação interativa em http://localhost:8000/docs
2. Leia EXAMPLES.md para casos de uso práticos
3. Estude a ARCHITECTURE.md para entender o design
4. Rode os testes para ver tudo funcionando
5. Modifique e estenda conforme necessário

## Contato

Para dúvidas, abra uma issue no repositório.

---

**Desenvolvido com FastAPI, SQLAlchemy e Python 3.9+**
