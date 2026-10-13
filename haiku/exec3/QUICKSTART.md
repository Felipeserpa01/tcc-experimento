# 🚀 Quick Start - Biblioteca API

Guia rápido para começar com a API.

## 1. Instalação

```bash
# Instalar dependências
pip install -r requirements.txt
```

## 2. Rodar a Aplicação

```bash
# Iniciar o servidor
uvicorn app.main:app --reload
```

A API estará em: **http://localhost:8000**

## 3. Acessar a Documentação

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 4. Rodar os Testes

```bash
# Executar todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=app --cov-report=html
```

## 5. Exemplo Prático Rápido

```bash
# Em outro terminal, executar o exemplo
python3 example_usage.py
```

## Fluxo Básico

### Registrar Usuário
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user123",
    "email": "user@example.com",
    "password": "Password123",
    "user_type": "reader"
  }'
```

### Fazer Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user123",
    "password": "Password123"
  }'
```

Copie o `access_token` da resposta.

### Usar a API
```bash
# Exemplo: listar livros
curl "http://localhost:8000/books/" \
  -H "Authorization: Bearer {YOUR_TOKEN}"
```

## Estrutura de Pastas

```
.
├── app/
│   ├── main.py           ← Aplicação principal
│   ├── database.py       ← Conexão com BD
│   ├── config.py         ← Configurações
│   ├── models/           ← Modelos SQLAlchemy
│   ├── schemas/          ← Validação Pydantic
│   ├── routes/           ← Endpoints
│   ├── security/         ← Autenticação JWT
│   └── utils/            ← Utilitários
├── tests/                ← Testes unitários
├── requirements.txt      ← Dependências
└── README.md             ← Documentação
```

## Endpoints Principais

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/auth/register` | Registrar usuário |
| POST | `/auth/login` | Fazer login |
| POST | `/books/` | Criar livro (bibliotecário) |
| GET | `/books/` | Listar livros |
| GET | `/books/search` | Buscar livros |
| POST | `/loans/` | Emprestar livro |
| GET | `/loans/user/active` | Meus empréstimos |
| POST | `/loans/return` | Devolver livro |

## Próximos Passos

1. Leia o README.md para documentação completa
2. Explore os testes em `tests/` para exemplos
3. Use o Swagger UI (`/docs`) para testar interativamente

## Troubleshooting

- **Erro 401**: Token inválido ou expirado → Faça login novamente
- **Erro 403**: Sem permissão → Apenas bibliotecários podem criar livros
- **Erro 422**: Dados inválidos → Verifique o formato da requisição
- **SQLite error**: Banco de dados corrompido → Delete `biblioteca.db` e reinicie

## Mudar Configurações

Edite `app/config.py` para customizar:

```python
MAX_LOANS_PER_USER = 3              # Máximo empréstimos
LOAN_DURATION_DAYS = 14             # Dias para devolver
LATE_FINE_PER_DAY = 5.0            # Multa diária
```

Bom trabalho! 📚
