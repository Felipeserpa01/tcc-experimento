import pytest

BOOK = {
    "title": "Dom Casmurro",
    "author": "Machado de Assis",
    "isbn": "978-0-306-40615-7",
    "year": 1899,
    "total_quantity": 3,
}


# ---------- Cadastro ----------


def test_librarian_creates_book(client, librarian_headers) -> None:
    response = client.post("/books", json=BOOK, headers=librarian_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["isbn"] == "9780306406157"  # normalizado, sem hífens
    assert body["total_quantity"] == 3
    assert body["available_quantity"] == 3


def test_reader_cannot_create_book(client, reader_headers) -> None:
    assert client.post("/books", json=BOOK, headers=reader_headers).status_code == 403


def test_anonymous_cannot_create_book(client) -> None:
    assert client.post("/books", json=BOOK).status_code == 401


@pytest.mark.parametrize(
    "override",
    [
        {"isbn": "978-0-306-40615-8"},  # dígito verificador errado
        {"year": 3000},
        {"total_quantity": 0},
        {"title": ""},
        {"available_quantity": 1},
    ],
)
def test_create_book_validates_input(client, librarian_headers, override: dict) -> None:
    response = client.post("/books", json=BOOK | override, headers=librarian_headers)
    assert response.status_code == 422


def test_create_book_missing_fields(client, librarian_headers) -> None:
    response = client.post("/books", json={"title": "Sem dados"}, headers=librarian_headers)

    assert response.status_code == 422
    missing = {error["loc"][-1] for error in response.json()["detail"]}
    assert missing == {"author", "isbn", "year", "total_quantity"}


def test_create_book_with_duplicate_isbn(client, librarian_headers) -> None:
    client.post("/books", json=BOOK, headers=librarian_headers)

    # Mesmo ISBN escrito de outra forma continua sendo duplicado.
    response = client.post("/books", json=BOOK | {"isbn": "9780306406157"}, headers=librarian_headers)

    assert response.status_code == 409


# ---------- Listagem e busca ----------


@pytest.fixture
def catalog(make_book) -> list[dict]:
    return [
        make_book(title="Dom Casmurro", author="Machado de Assis"),
        make_book(title="Memórias Póstumas de Brás Cubas", author="Machado de Assis"),
        make_book(title="O Cortiço", author="Aluísio Azevedo"),
        make_book(title="Vidas Secas", author="Graciliano Ramos"),
    ]


def test_any_authenticated_user_lists_books(client, reader_headers, catalog) -> None:
    response = client.get("/books", headers=reader_headers)

    assert response.status_code == 200
    assert len(response.json()) == 4


def test_list_books_requires_authentication(client) -> None:
    assert client.get("/books").status_code == 401


def test_search_by_title_is_partial_and_case_insensitive(client, reader_headers, catalog) -> None:
    response = client.get("/books", params={"title": "CASMURRO"}, headers=reader_headers)
    assert [book["title"] for book in response.json()] == ["Dom Casmurro"]


def test_search_by_author(client, reader_headers, catalog) -> None:
    response = client.get("/books", params={"author": "machado"}, headers=reader_headers)
    assert {book["title"] for book in response.json()} == {"Dom Casmurro", "Memórias Póstumas de Brás Cubas"}


def test_search_by_title_and_author_combined(client, reader_headers, catalog) -> None:
    response = client.get("/books", params={"title": "dom", "author": "machado"}, headers=reader_headers)
    assert [book["title"] for book in response.json()] == ["Dom Casmurro"]


def test_generic_search_matches_title_or_author(client, reader_headers, catalog) -> None:
    by_author = client.get("/books", params={"q": "ramos"}, headers=reader_headers).json()
    by_title = client.get("/books", params={"q": "cortiço"}, headers=reader_headers).json()

    assert [book["title"] for book in by_author] == ["Vidas Secas"]
    assert [book["title"] for book in by_title] == ["O Cortiço"]


def test_search_treats_wildcards_literally(client, reader_headers, catalog) -> None:
    response = client.get("/books", params={"title": "%"}, headers=reader_headers)
    assert response.json() == []


def test_list_books_pagination(client, reader_headers, catalog) -> None:
    page = client.get("/books", params={"skip": 1, "limit": 2}, headers=reader_headers)

    assert page.status_code == 200
    assert len(page.json()) == 2
    assert client.get("/books", params={"limit": 0}, headers=reader_headers).status_code == 422


def test_get_book_by_id(client, reader_headers, make_book) -> None:
    book = make_book()

    response = client.get(f"/books/{book['id']}", headers=reader_headers)

    assert response.status_code == 200
    assert response.json() == book


def test_get_unknown_book_returns_404(client, reader_headers) -> None:
    response = client.get("/books/99999", headers=reader_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Livro não encontrado."}


# ---------- Atualização ----------


def test_partial_update(client, librarian_headers, make_book) -> None:
    book = make_book(year=1990)

    response = client.patch(f"/books/{book['id']}", json={"title": "Título Revisado"}, headers=librarian_headers)

    assert response.status_code == 200
    assert response.json() == book | {"title": "Título Revisado"}


def test_update_rejects_null_and_unknown_fields(client, librarian_headers, make_book) -> None:
    book = make_book()

    assert client.patch(f"/books/{book['id']}", json={"title": None}, headers=librarian_headers).status_code == 422
    assert (
        client.patch(f"/books/{book['id']}", json={"available_quantity": 99}, headers=librarian_headers).status_code
        == 422
    )


def test_update_to_duplicate_isbn(client, librarian_headers, make_book) -> None:
    first = make_book()
    second = make_book()

    response = client.patch(f"/books/{second['id']}", json={"isbn": first["isbn"]}, headers=librarian_headers)

    assert response.status_code == 409


def test_update_keeping_same_isbn_is_allowed(client, librarian_headers, make_book) -> None:
    book = make_book()
    response = client.patch(f"/books/{book['id']}", json={"isbn": book["isbn"]}, headers=librarian_headers)
    assert response.status_code == 200


def test_update_total_quantity_recalculates_available(client, librarian_headers, make_book, reader, lend) -> None:
    book = make_book(total_quantity=3)
    lend(book["id"], reader.id)

    response = client.patch(f"/books/{book['id']}", json={"total_quantity": 5}, headers=librarian_headers)

    assert response.status_code == 200
    assert response.json()["total_quantity"] == 5
    assert response.json()["available_quantity"] == 4  # 5 exemplares - 1 emprestado


def test_update_total_below_loaned_copies_is_rejected(
    client, librarian_headers, make_book, make_user, lend
) -> None:
    book = make_book(total_quantity=2)
    lend(book["id"], make_user().id)
    lend(book["id"], make_user().id)

    response = client.patch(f"/books/{book['id']}", json={"total_quantity": 1}, headers=librarian_headers)

    assert response.status_code == 409
    assert client.get(f"/books/{book['id']}", headers=librarian_headers).json()["total_quantity"] == 2


def test_reader_cannot_update_book(client, reader_headers, make_book) -> None:
    book = make_book()
    assert client.patch(f"/books/{book['id']}", json={"title": "X"}, headers=reader_headers).status_code == 403


def test_update_unknown_book_returns_404(client, librarian_headers) -> None:
    assert client.patch("/books/99999", json={"title": "X"}, headers=librarian_headers).status_code == 404


# ---------- Remoção ----------


def test_delete_book(client, librarian_headers, make_book) -> None:
    book = make_book()

    response = client.delete(f"/books/{book['id']}", headers=librarian_headers)

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/books/{book['id']}", headers=librarian_headers).status_code == 404


def test_cannot_delete_book_with_active_loans(client, librarian_headers, make_book, reader, lend) -> None:
    book = make_book()
    loan = lend(book["id"], reader.id).json()

    assert client.delete(f"/books/{book['id']}", headers=librarian_headers).status_code == 409

    client.post(f"/loans/{loan['id']}/return", headers=librarian_headers)
    assert client.delete(f"/books/{book['id']}", headers=librarian_headers).status_code == 204


def test_reader_cannot_delete_book(client, reader_headers, make_book) -> None:
    book = make_book()
    assert client.delete(f"/books/{book['id']}", headers=reader_headers).status_code == 403


def test_delete_unknown_book_returns_404(client, librarian_headers) -> None:
    assert client.delete("/books/99999", headers=librarian_headers).status_code == 404

