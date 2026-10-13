# Exemplos de Uso - Library API

Este documento contém exemplos de requisições HTTP para testar a API.

## 1. Autenticação

### Registrar novo leitor
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "leitor@example.com",
    "full_name": "João Silva",
    "password": "senha123",
    "role": "reader"
  }'
```

Resposta esperada:
```json
{
  "id": 1,
  "email": "leitor@example.com",
  "full_name": "João Silva",
  "role": "reader"
}
```

### Registrar novo bibliotecário
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bibliotecario@example.com",
    "full_name": "Maria Santos",
    "password": "senha456",
    "role": "librarian"
  }'
```

### Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "leitor@example.com",
    "password": "senha123"
  }'
```

Resposta esperada:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "leitor@example.com",
    "full_name": "João Silva",
    "role": "reader"
  }
}
```

Salve o `access_token` para usar nas requisições autenticadas.

## 2. Gerenciamento de Livros

### Criar livro (bibliotecário)
```bash
TOKEN="seu_token_aqui"

curl -X POST "http://localhost:8000/books/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "isbn": "978-0132350884",
    "year": 2008,
    "total_quantity": 3
  }'
```

### Listar todos os livros
```bash
curl -X GET "http://localhost:8000/books/?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### Buscar livros por título ou autor
```bash
curl -X GET "http://localhost:8000/books/search?q=Clean" \
  -H "Authorization: Bearer $TOKEN"
```

### Obter detalhes de um livro
```bash
curl -X GET "http://localhost:8000/books/1" \
  -H "Authorization: Bearer $TOKEN"
```

### Atualizar livro (bibliotecário)
```bash
curl -X PUT "http://localhost:8000/books/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Clean Code - Revised Edition",
    "year": 2020
  }'
```

### Deletar livro (bibliotecário)
```bash
curl -X DELETE "http://localhost:8000/books/1" \
  -H "Authorization: Bearer $TOKEN"
```

## 3. Empréstimos

### Emprestar um livro (leitor)
```bash
LEITOR_TOKEN="token_do_leitor"

curl -X POST "http://localhost:8000/loans/" \
  -H "Authorization: Bearer $LEITOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 1
  }'
```

Resposta esperada:
```json
{
  "id": 1,
  "book_id": 1,
  "reader_id": 1,
  "loan_date": "2024-01-01T10:00:00",
  "due_date": "2024-01-15T10:00:00",
  "return_date": null,
  "fine": 0.0
}
```

### Listar empréstimos ativos do leitor
```bash
curl -X GET "http://localhost:8000/loans/" \
  -H "Authorization: Bearer $LEITOR_TOKEN"
```

### Devolver livro (no prazo)
```bash
curl -X POST "http://localhost:8000/loans/1/return" \
  -H "Authorization: Bearer $LEITOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "return_date": "2024-01-12T14:00:00"
  }'
```

Resposta: Multa = 0.0 (devolvido no prazo)

### Devolver livro (com atraso)
```bash
curl -X POST "http://localhost:8000/loans/1/return" \
  -H "Authorization: Bearer $LEITOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "return_date": "2024-01-25T14:00:00"
  }'
```

Resposta: Multa = 50.0 (10 dias de atraso × R$ 5,00)

## 4. Fluxo Completo de Teste

### Passo 1: Registre um bibliotecário
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bibliotecario@test.com",
    "full_name": "Admin",
    "password": "admin123",
    "role": "librarian"
  }'
```

### Passo 2: Login como bibliotecário
```bash
BIBLIOTECARIO=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bibliotecario@test.com",
    "password": "admin123"
  }' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

echo "Bibliotecário Token: $BIBLIOTECARIO"
```

### Passo 3: Adicione alguns livros
```bash
curl -X POST "http://localhost:8000/books/" \
  -H "Authorization: Bearer $BIBLIOTECARIO" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Pragmatic Programmer",
    "author": "David Thomas",
    "isbn": "978-0135957059",
    "year": 2019,
    "total_quantity": 5
  }'
```

### Passo 4: Registre um leitor
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "leitor@test.com",
    "full_name": "João",
    "password": "leitor123",
    "role": "reader"
  }'
```

### Passo 5: Login como leitor
```bash
LEITOR=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "leitor@test.com",
    "password": "leitor123"
  }' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

echo "Leitor Token: $LEITOR"
```

### Passo 6: Emprestar um livro
```bash
curl -X POST "http://localhost:8000/loans/" \
  -H "Authorization: Bearer $LEITOR" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 1
  }'
```

### Passo 7: Listar empréstimos
```bash
curl -X GET "http://localhost:8000/loans/" \
  -H "Authorization: Bearer $LEITOR"
```

### Passo 8: Devolver o livro
```bash
curl -X POST "http://localhost:8000/loans/1/return" \
  -H "Authorization: Bearer $LEITOR" \
  -H "Content-Type: application/json" \
  -d '{
    "return_date": "2024-01-10T15:00:00"
  }'
```

## Usando Postman

1. Crie uma coleção chamada "Library API"
2. Crie variáveis de ambiente:
   - `base_url`: http://localhost:8000
   - `librarian_token`: (atualizada após login)
   - `reader_token`: (atualizada após login)

3. Use `{{base_url}}` e `{{token}}` nas URLs e headers

Exemplo de URL no Postman:
```
{{base_url}}/books/
```

Header de autenticação:
```
Authorization: Bearer {{reader_token}}
```

## Tratamento de Erros

### Erro 400 - Requisição inválida
```json
{
  "detail": "Email already registered"
}
```

### Erro 401 - Não autenticado
```json
{
  "detail": "Could not validate credentials"
}
```

### Erro 403 - Acesso negado
```json
{
  "detail": "Only librarians can manage books"
}
```

### Erro 404 - Não encontrado
```json
{
  "detail": "Book not found"
}
```

## Dicas

- Sempre incluir header `Authorization: Bearer {token}`
- A data/hora deve estar em formato ISO 8601
- A multa é calculada automaticamente como: dias de atraso × R$ 5,00
- Máximo 3 empréstimos simultâneos por leitor
- Use `/docs` para acessar a documentação interativa do Swagger
