# API de Gerenciamento de Biblioteca

API REST em **Python + FastAPI** para gerenciar o acervo, os usuários e os empréstimos de uma biblioteca.
Usa SQLite (via SQLAlchemy 2), autenticação JWT, senhas com hash Argon2id e testes com pytest.

## Estrutura

```
.
├── app/
│   ├── main.py              # criação da aplicação FastAPI e registro das rotas
│   ├── cli.py               # comando para criar o primeiro bibliotecário
│   ├── api/
│   │   ├── deps.py          # dependências: sessão do banco, usuário autenticado, permissões
│   │   └── routes/          # camada HTTP: auth, users, books, loans
│   ├── core/
│   │   ├── config.py        # configurações (variáveis de ambiente / .env)
│   │   ├── security.py      # hash de senha e tokens JWT
│   │   ├── exceptions.py    # erros de domínio e conversão para respostas HTTP
│   │   └── clock.py         # data atual (injetável nos testes)
│   ├── db/                  # engine, sessão e base declarativa
│   ├── models/              # modelos SQLAlchemy: User, Book, Loan
│   ├── schemas/             # schemas Pydantic de entrada e saída (validação)
│   └── services/            # regras de negócio (independentes de HTTP)
│       └── fines.py         # cálculo de multa (funções puras)
├── tests/                   # testes unitários e de integração (pytest)
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

As rotas só tratam HTTP; as regras ficam em `services/`, que lançam exceções de domínio
(`NotFoundError`, `ConflictError`...). Essas exceções viram respostas HTTP em um único lugar
(`core/exceptions.py`).

## Como executar

Requer Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env        # ajuste o SECRET_KEY

# O cadastro público cria apenas leitores. Crie o primeiro bibliotecário pela linha de comando:
python -m app.cli create-librarian --name "Maria Silva" --email maria@biblioteca.com

uvicorn app.main:app --reload
```

As tabelas são criadas automaticamente na inicialização. A documentação interativa fica em
**http://localhost:8000/docs**. Para autenticar no Swagger, clique em **Authorize** e informe o e-mail no
campo `username`.

## Configuração

| Variável                      | Padrão                   | Descrição                                   |
|-------------------------------|--------------------------|---------------------------------------------|
| `DATABASE_URL`                | `sqlite:///./library.db` | Conexão com o banco                         |
| `SECRET_KEY`                  | *(aleatória)*            | Chave de assinatura do JWT                  |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                     | Validade do token                           |
| `LOAN_PERIOD_DAYS`            | `14`                     | Prazo padrão do empréstimo                  |
| `MAX_ACTIVE_LOANS`            | `3`                      | Empréstimos simultâneos por leitor          |
| `DAILY_FINE`                  | `2.00`                   | Multa por dia de atraso                     |

> Se `SECRET_KEY` não for definida, uma chave temporária é gerada a cada inicialização (os tokens
> deixam de valer quando o servidor reinicia). Em produção, sempre defina uma chave fixa.

## Perfis e endpoints

Há dois perfis: **bibliotecário** (`librarian`) e **leitor** (`reader`). Todas as rotas, exceto
cadastro, login e `/health`, exigem o header `Authorization: Bearer <token>`.

| Método   | Rota                        | Acesso               | Descrição                                        |
|----------|-----------------------------|----------------------|--------------------------------------------------|
| `POST`   | `/auth/register`            | público              | Cadastro de leitor                               |
| `POST`   | `/auth/login`               | público              | Login com JSON (`email`, `password`)             |
| `POST`   | `/auth/token`               | público              | Login com formulário OAuth2 (Swagger)            |
| `GET`    | `/users/me`                 | autenticado          | Dados do próprio usuário                         |
| `GET`    | `/users/me/loans`           | autenticado          | Próprios empréstimos (`active_only=true` padrão) |
| `GET`    | `/users`                    | bibliotecário        | Lista usuários (filtro `role`)                   |
| `POST`   | `/users`                    | bibliotecário        | Cria usuário de qualquer perfil                  |
| `GET`    | `/users/{id}`               | bibliotecário ou o próprio | Consulta usuário                           |
| `GET`    | `/users/{id}/loans`         | bibliotecário ou o próprio | **Empréstimos ativos do leitor**           |
| `GET`    | `/books`                    | autenticado          | Lista/busca (`title`, `author`, `q`, `skip`, `limit`) |
| `GET`    | `/books/{id}`               | autenticado          | Consulta livro                                   |
| `POST`   | `/books`                    | bibliotecário        | Cadastra livro                                   |
| `PATCH`  | `/books/{id}`               | bibliotecário        | Atualização parcial                              |
| `DELETE` | `/books/{id}`               | bibliotecário        | Remove livro                                     |
| `POST`   | `/loans`                    | bibliotecário        | Registra empréstimo                              |
| `GET`    | `/loans`                    | bibliotecário        | Lista (`reader_id`, `book_id`, `active_only`, `overdue_only`) |
| `GET`    | `/loans/{id}`               | bibliotecário ou o leitor do empréstimo | Consulta empréstimo           |
| `POST`   | `/loans/{id}/return`        | bibliotecário        | Registra devolução e calcula multa               |

### Exemplo de uso

```bash
TOKEN=$(curl -s -X POST localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"maria@biblioteca.com","password":"suaSenha123"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -X POST localhost:8000/books -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Dom Casmurro","author":"Machado de Assis","isbn":"978-0-306-40615-7","year":1899,"total_quantity":2}'

curl -X POST localhost:8000/loans -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"book_id":1,"reader_id":2}'
```

## Regras de negócio

**Livros**
- `available_quantity` é controlada pelo sistema: começa igual a `total_quantity`, diminui no empréstimo
  e aumenta na devolução. Enviar esse campo na entrada é recusado (422).
- Ao alterar `total_quantity`, a disponibilidade é recalculada (`total − exemplares emprestados`). Não é
  possível reduzir o total abaixo do número de exemplares emprestados (409).
- O ISBN é validado (ISBN-10 ou ISBN-13, com dígito verificador), normalizado sem hífens e é único.
- A busca é parcial e não diferencia maiúsculas de minúsculas.
- Um livro com empréstimos ativos não pode ser removido (409). Ao remover um livro sem empréstimos
  ativos, o histórico de empréstimos já devolvidos dele também é apagado.

**Empréstimos**
- Somente usuários do perfil leitor podem receber empréstimos.
- Não é permitido emprestar um livro sem exemplares disponíveis (409).
- Cada leitor pode ter no máximo **3** empréstimos ativos ao mesmo tempo (409).
- A data prevista é `data do empréstimo + LOAN_PERIOD_DAYS` (ou `loan_days`, de 1 a 90, se informado).
- A reserva do exemplar e a devolução usam `UPDATE` condicional, o que impede emprestar o último exemplar
  duas vezes ou registrar a mesma devolução em duplicidade quando há requisições simultâneas.

**Multa**
- `multa = max(0, data real de devolução − data prevista) em dias × DAILY_FINE`.
- Na devolução, a multa é calculada e **gravada**; mudanças posteriores no valor diário não alteram o
  histórico.
- Para empréstimos ainda ativos e atrasados, a resposta mostra `status: "overdue"` e a multa acumulada até
  hoje.
- Valores são calculados com `Decimal` e armazenados em centavos (inteiros).

## Erros

Todas as respostas de erro seguem o formato `{"detail": ...}`.

| Código | Quando                                                                           |
|--------|----------------------------------------------------------------------------------|
| 401    | Token ausente, inválido ou expirado; credenciais incorretas                      |
| 403    | Perfil sem permissão ou acesso a dados de outro leitor                           |
| 404    | Livro, usuário ou empréstimo inexistente                                         |
| 409    | E-mail/ISBN duplicado, sem exemplares, limite de empréstimos, devolução repetida |
| 422    | Dados de entrada inválidos, ou empréstimo para usuário que não é leitor          |

## Testes

```bash
pytest                          # executa a suíte
pytest --cov=app                # com relatório de cobertura
```

São 136 testes, com cobertura de 97%. Cada teste usa um banco SQLite em memória isolado.
A data atual é injetada por dependência (`get_today`), então os testes de multa simulam a passagem dos
dias sem depender do relógio do sistema.

| Arquivo             | O que cobre                                                              |
|---------------------|--------------------------------------------------------------------------|
| `test_fines.py`     | Cálculo de dias de atraso e multa (unitário)                             |
| `test_security.py`  | Hash de senha e emissão/validação de JWT (unitário)                      |
| `test_schemas.py`   | Validação de ISBN, ano, quantidades, senha e e-mail (unitário)           |
| `test_auth.py`      | Cadastro, login e rejeição de tokens inválidos                           |
| `test_users.py`     | Permissões por perfil e gestão de usuários                               |
| `test_books.py`     | CRUD, busca, paginação e regras de quantidade                            |
| `test_loans.py`     | Empréstimo, limites, devolução, multa e consultas                        |
| `test_cli.py`       | Criação de bibliotecário pela linha de comando                           |

## Possíveis evoluções

- Migrações de esquema com Alembic (hoje as tabelas são criadas com `create_all`).
- Refresh tokens e revogação de sessões.
- Renovação de empréstimos e pagamento de multas.
