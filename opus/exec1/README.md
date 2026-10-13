# Biblioteca API

API REST para gerenciamento de biblioteca feita com **FastAPI**, **SQLAlchemy 2** e **SQLite**:
usuários com autenticação JWT, CRUD de livros e controle de empréstimos com multa por atraso.

## Stack

| Camada          | Tecnologia                                   |
| --------------- | -------------------------------------------- |
| Framework web   | FastAPI + Uvicorn                            |
| Banco de dados  | SQLite via SQLAlchemy 2.0 (ORM)              |
| Validação       | Pydantic v2 / pydantic-settings              |
| Autenticação    | JWT (PyJWT) + OAuth2 Password flow           |
| Hash de senhas  | Argon2 (pwdlib)                              |
| Testes          | pytest, pytest-cov, TestClient do FastAPI    |

## Estrutura de pastas

```
.
├── app/
│   ├── main.py               # Criação da aplicação, rotas e inicialização do banco
│   ├── api/
│   │   ├── deps.py           # Dependências: sessão, usuário atual, permissões, paginação, data atual
│   │   └── routes/           # Endpoints: auth, users, books, loans
│   ├── core/
│   │   ├── config.py         # Configurações (variáveis de ambiente / .env)
│   │   ├── security.py       # Hash de senha e geração/validação de JWT
│   │   ├── exceptions.py     # Erros de domínio e handlers HTTP
│   │   └── isbn.py           # Validação de ISBN-10/ISBN-13
│   ├── db/
│   │   ├── base.py           # Base declarativa
│   │   ├── session.py        # Engine, sessão e get_db
│   │   └── types.py          # Tipo datetime sempre em UTC
│   ├── models/               # Modelos ORM: User, Book, Loan
│   ├── schemas/              # Schemas Pydantic de entrada e saída
│   └── services/             # Regras de negócio (usuários, livros, empréstimos, multas)
├── tests/
│   ├── conftest.py           # Banco em memória, cliente HTTP, relógio controlável e factories
│   ├── unit/                 # Testes de funções puras, schemas e serviços
│   └── api/                  # Testes dos endpoints (status HTTP, permissões, fluxos)
├── .env.example
├── pyproject.toml            # Configuração do pytest e do ruff
├── requirements.txt
└── requirements-dev.txt
```

A organização segue camadas: **rotas** tratam HTTP e permissões, **serviços** concentram as regras de
negócio e **modelos** representam o banco. Assim as regras podem ser testadas sem passar pelo HTTP.

## Como executar

Requer Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env               # ajuste SECRET_KEY e o bibliotecário inicial
uvicorn app.main:app --reload
```

- Documentação interativa (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

As tabelas são criadas automaticamente na inicialização. Se `FIRST_LIBRARIAN_EMAIL` e
`FIRST_LIBRARIAN_PASSWORD` estiverem definidos, esse bibliotecário é criado caso ainda não exista.
Ele é necessário porque apenas bibliotecários podem cadastrar outros bibliotecários.

No Swagger, clique em **Authorize** e informe o e-mail no campo `username` e a senha.

## Configuração

| Variável                      | Padrão                    | Descrição                                     |
| ----------------------------- | ------------------------- | --------------------------------------------- |
| `DATABASE_URL`                | `sqlite:///./library.db`  | URL do banco                                  |
| `SECRET_KEY`                  | chave de desenvolvimento  | Chave de assinatura do JWT (**troque em produção**) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                      | Validade do token                             |
| `LOAN_PERIOD_DAYS`            | `14`                      | Prazo padrão de devolução                     |
| `MAX_ACTIVE_LOANS`            | `3`                       | Empréstimos simultâneos por leitor            |
| `DAILY_FINE`                  | `2.00`                    | Multa por dia de atraso                       |
| `FIRST_LIBRARIAN_NAME/EMAIL/PASSWORD` | —                 | Bibliotecário criado na inicialização         |

## Endpoints

Todas as rotas, exceto registro, login e `/health`, exigem o header `Authorization: Bearer <token>`.

### Autenticação e usuários

| Método | Rota                             | Acesso                     | Descrição |
| ------ | -------------------------------- | -------------------------- | --------- |
| POST   | `/auth/register`                 | Público*                   | Cadastra usuário (`role`: `reader` ou `librarian`) |
| POST   | `/auth/login`                    | Público                    | Login (form: `username`=e-mail, `password`) e retorno do JWT |
| GET    | `/users/me`                      | Autenticado                | Dados do usuário logado |
| GET    | `/users`                         | Bibliotecário              | Lista usuários (filtro `role`, paginação) |
| GET    | `/users/{id}`                    | Bibliotecário ou o próprio | Detalhes do usuário |
| GET    | `/users/{id}/loans/active`       | Bibliotecário ou o próprio | Empréstimos ativos do leitor |

\* Cadastrar um **bibliotecário** exige um token de bibliotecário. Leitores podem se cadastrar livremente.

### Livros

| Método | Rota           | Acesso        | Descrição |
| ------ | -------------- | ------------- | --------- |
| POST   | `/books`       | Bibliotecário | Cadastra livro |
| GET    | `/books`       | Autenticado   | Lista/busca: `q` (título ou autor), `title`, `author`, `available_only`, `skip`, `limit` |
| GET    | `/books/{id}`  | Autenticado   | Detalhes do livro |
| PATCH  | `/books/{id}`  | Bibliotecário | Atualização parcial |
| DELETE | `/books/{id}`  | Bibliotecário | Remove livro |

### Empréstimos

| Método | Rota                   | Acesso                     | Descrição |
| ------ | ---------------------- | -------------------------- | --------- |
| POST   | `/loans`               | Bibliotecário              | Registra empréstimo (`book_id`, `reader_id`, `due_date` opcional) |
| POST   | `/loans/{id}/return`   | Bibliotecário              | Registra devolução e calcula a multa |
| GET    | `/loans`               | Autenticado                | Lista empréstimos (filtros `reader_id`, `status`, `overdue`). Leitores veem só os próprios |
| GET    | `/loans/{id}`          | Bibliotecário ou o leitor  | Detalhes do empréstimo |
| GET    | `/loans/{id}/fine`     | Bibliotecário ou o leitor  | Cálculo da multa |

## Regras de negócio

**Livros**
- ISBN-10 ou ISBN-13 com dígito verificador válido. Hífens e espaços são removidos e o ISBN é único.
- O ano não pode estar no futuro e a quantidade total vai de 1 a 10.000.
- No cadastro, `available_quantity` começa igual a `total_quantity`. Depois disso ela é controlada
  pelos empréstimos e não pode ser editada diretamente.
- Ao alterar `total_quantity`, os exemplares emprestados são mantidos: o novo total não pode ser menor
  que a quantidade emprestada (409).
- Livros com empréstimos ativos não podem ser removidos (409). Ao remover um livro, o histórico de
  empréstimos já devolvidos é removido junto.

**Empréstimos**
- Só podem ser feitos para usuários com papel `reader` (422).
- Sem exemplares disponíveis, retorna **409** `book_unavailable`. A baixa do exemplar é feita com um
  `UPDATE` condicional, então duas requisições simultâneas não conseguem emprestar o último exemplar.
- Cada leitor pode ter no máximo **3** empréstimos ativos. O 4º retorna **409** `loan_limit_reached`.
- Prazo padrão de 14 dias. Uma `due_date` personalizada precisa ser posterior à data do empréstimo.
- Um empréstimo não pode ser devolvido duas vezes (409).

**Multa**
- `multa = dias de atraso × DAILY_FINE`, sendo `dias de atraso = max(0, data real − data prevista)`.
- Devolução no dia previsto ou antes dele não gera multa.
- Na devolução, a multa é calculada e **gravada**, e não muda mais.
- Enquanto o empréstimo está ativo, `fine_amount` e `/loans/{id}/fine` mostram a multa acumulada até hoje.
- Valores monetários são retornados como string decimal (ex.: `"12.00"`) para evitar erros de ponto flutuante.

## Tratamento de erros

Erros de negócio retornam um corpo padronizado com mensagem e código estável:

```json
{ "detail": "Não há exemplares disponíveis deste livro", "code": "book_unavailable" }
```

| Status | Quando |
| ------ | ------ |
| 401    | Token ausente, inválido ou expirado, ou credenciais incorretas |
| 403    | Usuário sem permissão (ex.: leitor tentando cadastrar livro) |
| 404    | Recurso não encontrado |
| 409    | Conflito com o estado atual: e-mail/ISBN duplicado, livro indisponível, limite de empréstimos, devolução repetida |
| 422    | Dados inválidos (validação do Pydantic) ou regra violada (ex.: empréstimo para bibliotecário) |
| 500    | Erro inesperado (resposta genérica, detalhes só no log) |

## Exemplo de uso (curl)

```bash
# Login do bibliotecário inicial
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -d "username=admin@biblioteca.com&password=admin12345" | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Cadastro de leitor (público)
curl -X POST localhost:8000/auth/register -H "Content-Type: application/json" \
  -d '{"name":"Maria","email":"maria@example.com","password":"maria1234"}'

# Cadastro de livro
curl -X POST localhost:8000/books -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Dom Casmurro","author":"Machado de Assis","isbn":"978-0-306-40615-7","year":1899,"total_quantity":2}'

# Empréstimo e devolução
curl -X POST localhost:8000/loans -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"book_id":1,"reader_id":2}'
curl -X POST localhost:8000/loans/1/return -H "Authorization: Bearer $TOKEN"
```

## Testes

```bash
pytest                            # roda todos os testes
pytest --cov=app                  # com relatório de cobertura
pytest tests/unit                 # só os testes unitários
```

- Cada teste usa um **SQLite em memória** novo, então os testes são isolados e não tocam no banco real.
- A data atual é injetada pela dependência `get_today`. Nos testes ela é substituída por um relógio
  controlável (`clock.advance(dias)`), o que permite testar atrasos e multas sem esperar dias.
- `tests/unit`: cálculo de multa, validação de ISBN, hash/JWT, schemas e regras dos serviços.
- `tests/api`: endpoints de ponta a ponta, com códigos HTTP, permissões por papel e o fluxo completo
  de cadastro, empréstimo, atraso e devolução com multa.

Estado atual: **151 testes passando, cobertura de 97%**.

## Possíveis evoluções

- Migrações com Alembic, em vez de `create_all`, para evoluir o esquema em produção.
- Refresh tokens e revogação de tokens.
- Renovação de empréstimos e reservas.
