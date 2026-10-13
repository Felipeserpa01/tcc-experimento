# Exemplos de Uso da API de Biblioteca

## 1. Registro e Autenticação

### Registrar um novo bibliotecário

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "maria_silva",
    "email": "maria@biblioteca.com",
    "password": "senha_segura_123",
    "is_librarian": true
  }'
```

**Resposta:**
```json
{
  "id": 1,
  "username": "maria_silva",
  "email": "maria@biblioteca.com",
  "is_librarian": true,
  "created_at": "2024-09-13T10:30:00"
}
```

### Registrar um novo leitor

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "joao_leitor",
    "email": "joao@example.com",
    "password": "senha_do_joao",
    "is_librarian": false
  }'
```

### Login e obter token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "joao_leitor",
    "password": "senha_do_joao"
  }'
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 2,
    "username": "joao_leitor",
    "email": "joao@example.com",
    "is_librarian": false,
    "created_at": "2024-09-13T10:35:00"
  }
}
```

Salve o `access_token` para usar nos próximos requests.

---

## 2. Gerenciamento de Livros

### Criar um novo livro (Apenas bibliotecário)

```bash
TOKEN="seu_token_do_bibliotecario"

curl -X POST http://localhost:8000/api/books/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "O Senhor dos Anéis",
    "author": "J.R.R. Tolkien",
    "isbn": "978-8516059057",
    "year": 1954,
    "total_quantity": 5
  }'
```

**Resposta:**
```json
{
  "id": 1,
  "title": "O Senhor dos Anéis",
  "author": "J.R.R. Tolkien",
  "isbn": "978-8516059057",
  "year": 1954,
  "total_quantity": 5,
  "available_quantity": 5,
  "created_at": "2024-09-13T11:00:00"
}
```

### Criar mais livros

```bash
TOKEN="seu_token_do_bibliotecario"

curl -X POST http://localhost:8000/api/books/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell",
    "isbn": "978-0451524935",
    "year": 1949,
    "total_quantity": 3
  }'

curl -X POST http://localhost:8000/api/books/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Dom Casmurro",
    "author": "Machado de Assis",
    "isbn": "978-8525410882",
    "year": 1899,
    "total_quantity": 4
  }'
```

### Listar todos os livros

```bash
TOKEN="seu_token_de_leitor"

curl -X GET http://localhost:8000/api/books/ \
  -H "Authorization: Bearer $TOKEN"
```

**Resposta:**
```json
[
  {
    "id": 1,
    "title": "O Senhor dos Anéis",
    "author": "J.R.R. Tolkien",
    "isbn": "978-8516059057",
    "year": 1954,
    "total_quantity": 5,
    "available_quantity": 5,
    "created_at": "2024-09-13T11:00:00"
  },
  {
    "id": 2,
    "title": "1984",
    "author": "George Orwell",
    "isbn": "978-0451524935",
    "year": 1949,
    "total_quantity": 3,
    "available_quantity": 3,
    "created_at": "2024-09-13T11:05:00"
  }
]
```

### Buscar livro por título

```bash
curl -X GET "http://localhost:8000/api/books/search/by-title?title=Senhor" \
  -H "Authorization: Bearer $TOKEN"
```

### Buscar livro por autor

```bash
curl -X GET "http://localhost:8000/api/books/search/by-author?author=Tolkien" \
  -H "Authorization: Bearer $TOKEN"
```

### Obter detalhes de um livro

```bash
curl -X GET http://localhost:8000/api/books/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Atualizar um livro (Apenas bibliotecário)

```bash
TOKEN="seu_token_do_bibliotecario"

curl -X PUT http://localhost:8000/api/books/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "O Senhor dos Anéis - Edição Especial",
    "total_quantity": 8
  }'
```

### Deletar um livro (Apenas bibliotecário)

```bash
curl -X DELETE http://localhost:8000/api/books/3 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 3. Gerenciamento de Empréstimos

### Emprestar um livro

```bash
TOKEN="seu_token_de_leitor"

curl -X POST http://localhost:8000/api/loans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 1
  }'
```

**Resposta:**
```json
{
  "id": 1,
  "user_id": 2,
  "book_id": 1,
  "loan_date": "2024-09-13T14:00:00",
  "due_date": "2024-09-27T14:00:00",
  "return_date": null,
  "fine": 0.0
}
```

### Emprestar múltiplos livros (até 3 por leitor)

```bash
curl -X POST http://localhost:8000/api/loans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 2}'

curl -X POST http://localhost:8000/api/loans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 3}'
```

### Tentar emprestar 4º livro (deve falhar)

```bash
curl -X POST http://localhost:8000/api/loans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 4}'
```

**Resposta (erro):**
```json
{
  "detail": "Limite de 3 empréstimos simultâneos atingido"
}
```

### Devolver um livro no prazo

```bash
TOKEN="seu_token_de_leitor"

curl -X POST http://localhost:8000/api/loans/1/return \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "return_date": "2024-09-20T10:00:00Z"
  }'
```

**Resposta:**
```json
{
  "id": 1,
  "user_id": 2,
  "book_id": 1,
  "loan_date": "2024-09-13T14:00:00",
  "due_date": "2024-09-27T14:00:00",
  "return_date": "2024-09-20T10:00:00Z",
  "fine": 0.0
}
```

### Devolver um livro com atraso (7 dias)

```bash
curl -X POST http://localhost:8000/api/loans/2/return \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "return_date": "2024-10-04T14:00:00Z"
  }'
```

**Resposta (com multa):**
```json
{
  "id": 2,
  "user_id": 2,
  "book_id": 2,
  "loan_date": "2024-09-13T14:00:00",
  "due_date": "2024-09-27T14:00:00",
  "return_date": "2024-10-04T14:00:00Z",
  "fine": 35.0
}
```

### Listar meus empréstimos

```bash
curl -X GET http://localhost:8000/api/loans/my-loans \
  -H "Authorization: Bearer $TOKEN"
```

### Ver empréstimos ativos de um leitor (Biblioteca ou próprio usuário)

```bash
curl -X GET http://localhost:8000/api/loans/active-loans/2 \
  -H "Authorization: Bearer $TOKEN"
```

### Listar todos os empréstimos (Apenas bibliotecário)

```bash
TOKEN="seu_token_do_bibliotecario"

curl -X GET http://localhost:8000/api/loans/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## 4. Cenários de Erro

### Tentar emprestar sem exemplares disponíveis

Suponha que o livro 1 tem 0 exemplares disponíveis:

```bash
curl -X POST http://localhost:8000/api/loans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 1}'
```

**Resposta (erro 400):**
```json
{
  "detail": "Nenhum exemplar disponível deste livro"
}
```

### Tentar acessar recurso sem permissão

```bash
TOKEN="seu_token_de_leitor"

curl -X POST http://localhost:8000/api/books/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Livro",
    "author": "Autor",
    "isbn": "123",
    "year": 2024,
    "total_quantity": 1
  }'
```

**Resposta (erro 403):**
```json
{
  "detail": "Apenas bibliotecários podem acessar este recurso"
}
```

### Token expirado ou inválido

```bash
curl -X GET http://localhost:8000/api/books/ \
  -H "Authorization: Bearer token_invalido"
```

**Resposta (erro 401):**
```json
{
  "detail": "Token inválido ou expirado"
}
```

---

## 5. Usando Python Requests

```python
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = "http://localhost:8000/api"

# 1. Registrar usuário
response = requests.post(
    f"{BASE_URL}/auth/register",
    json={
        "username": "pedro",
        "email": "pedro@example.com",
        "password": "senha123",
        "is_librarian": False
    }
)
print(response.json())

# 2. Login
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"username": "pedro", "password": "senha123"}
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Listar livros
response = requests.get(f"{BASE_URL}/books/", headers=headers)
books = response.json()
print(books)

# 4. Emprestar um livro
response = requests.post(
    f"{BASE_URL}/loans/",
    json={"book_id": 1},
    headers=headers
)
loan = response.json()
print(f"Emprestado! Due date: {loan['due_date']}")

# 5. Devolver o livro
return_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
response = requests.post(
    f"{BASE_URL}/loans/{loan['id']}/return",
    json={"return_date": return_date},
    headers=headers
)
returned_loan = response.json()
print(f"Devolvido! Multa: R$ {returned_loan['fine']}")
```

---

## 6. Documentação Interativa

Acesse a documentação interativa em:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Lá você pode testar todos os endpoints diretamente no navegador!
