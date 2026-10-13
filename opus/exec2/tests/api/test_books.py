from datetime import date

import pytest

from tests.conftest import make_isbn

BOOK = {
    "title": "Memórias Póstumas de Brás Cubas",
    "author": "Machado de Assis",
    "isbn": "978-0-306-40615-7",
    "year": 1881,
    "total_quantity": 3,
}


def test_librarian_creates_book(client, librarian_headers):
    response = client.post("/books", json=BOOK, headers=librarian_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["isbn"] == "9780306406157"
    assert body["total_quantity"] == body["available_quantity"] == 3


def test_reader_cannot_create_book(client, reader_headers):
    assert client.post("/books", json=BOOK, headers=reader_headers).status_code == 403


def test_create_book_requires_authentication(client):
    assert client.post("/books", json=BOOK).status_code == 401


def test_duplicate_isbn_returns_409_even_in_another_format(client, librarian_headers):
    client.post("/books", json=BOOK, headers=librarian_headers)
    response = client.post("/books", json={**BOOK, "isbn": "0-306-40615-2"}, headers=librarian_headers)

    assert response.status_code == 409
    assert response.json()["code"] == "isbn_already_registered"


@pytest.mark.parametrize(
    "overrides",
    [
        {"isbn": "978-0-306-40615-8"},
        {"total_quantity": 0},
        {"total_quantity": "3"},
        {"year": date.today().year + 1},
        {"title": ""},
        {"available_quantity": 99},
    ],
)
def test_create_book_with_invalid_data_returns_422(client, librarian_headers, overrides):
    response = client.post("/books", json={**BOOK, **overrides}, headers=librarian_headers)
    assert response.status_code == 422


def test_missing_fields_return_422(client, librarian_headers):
    response = client.post("/books", json={"title": "Só título"}, headers=librarian_headers)

    assert response.status_code == 422
    missing = {error["loc"][-1] for error in response.json()["detail"]}
    assert missing == {"author", "isbn", "year", "total_quantity"}


def test_list_books_is_paginated(client, reader_headers, make_book):
    for _ in range(5):
        make_book()

    response = client.get("/books", params={"skip": 1, "limit": 2}, headers=reader_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert (body["skip"], body["limit"]) == (1, 2)


def test_search_books_by_title_or_author(client, reader_headers, make_book):
    make_book(title="Ensaio sobre a Cegueira", author="José Saramago")
    make_book(title="O Evangelho segundo Jesus Cristo", author="José Saramago")
    make_book(title="Dom Casmurro", author="Machado de Assis")

    def titles(**params):
        response = client.get("/books", params=params, headers=reader_headers)
        assert response.status_code == 200
        return sorted(book["title"] for book in response.json()["items"])

    assert titles(title="cegueira") == ["Ensaio sobre a Cegueira"]
    assert titles(author="jose saramago") == ["Ensaio sobre a Cegueira", "O Evangelho segundo Jesus Cristo"]
    assert titles(q="MACHADO") == ["Dom Casmurro"]
    assert titles(q="casmurro") == ["Dom Casmurro"]
    assert titles(q="inexistente") == []


def test_search_treats_like_wildcards_literally(client, reader_headers, make_book):
    make_book(title="100% Python")
    make_book(title="Python Avançado")

    response = client.get("/books", params={"q": "100%"}, headers=reader_headers)
    assert [book["title"] for book in response.json()["items"]] == ["100% Python"]


def test_filter_by_availability(client, reader_headers, make_book, make_user, librarian_headers):
    borrowed = make_book(title="Emprestado")
    make_book(title="Disponível")
    client.post("/loans", json={"book_id": borrowed.id, "reader_id": make_user().id}, headers=librarian_headers)

    available = client.get("/books", params={"available": True}, headers=reader_headers).json()
    unavailable = client.get("/books", params={"available": False}, headers=reader_headers).json()

    assert [book["title"] for book in available["items"]] == ["Disponível"]
    assert [book["title"] for book in unavailable["items"]] == ["Emprestado"]


def test_get_book(client, reader_headers, make_book):
    book = make_book()

    assert client.get(f"/books/{book.id}", headers=reader_headers).json()["isbn"] == book.isbn
    assert client.get("/books/999", headers=reader_headers).status_code == 404


def test_partial_update(client, librarian_headers, make_book):
    book = make_book(title="Título antigo", year=1990)

    response = client.patch(f"/books/{book.id}", json={"title": "Título novo"}, headers=librarian_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Título novo"
    assert body["year"] == 1990


def test_update_to_existing_isbn_returns_409(client, librarian_headers, make_book):
    first = make_book()
    second = make_book()

    response = client.patch(f"/books/{second.id}", json={"isbn": first.isbn}, headers=librarian_headers)
    assert response.status_code == 409


def test_update_with_invalid_payload_returns_422(client, librarian_headers, make_book):
    book = make_book()

    assert client.patch(f"/books/{book.id}", json={}, headers=librarian_headers).status_code == 422
    assert client.patch(f"/books/{book.id}", json={"title": None}, headers=librarian_headers).status_code == 422


def test_changing_total_quantity_keeps_loaned_copies(client, librarian_headers, make_book, make_user):
    book = make_book(total_quantity=3)
    for _ in range(2):
        client.post("/loans", json={"book_id": book.id, "reader_id": make_user().id}, headers=librarian_headers)

    increased = client.patch(f"/books/{book.id}", json={"total_quantity": 5}, headers=librarian_headers)
    assert increased.status_code == 200
    assert (increased.json()["total_quantity"], increased.json()["available_quantity"]) == (5, 3)

    below_loaned = client.patch(f"/books/{book.id}", json={"total_quantity": 1}, headers=librarian_headers)
    assert below_loaned.status_code == 409
    assert below_loaned.json()["code"] == "total_below_loaned"


def test_reader_cannot_update_or_delete(client, reader_headers, make_book):
    book = make_book()

    assert client.patch(f"/books/{book.id}", json={"title": "X"}, headers=reader_headers).status_code == 403
    assert client.delete(f"/books/{book.id}", headers=reader_headers).status_code == 403


def test_delete_book(client, librarian_headers, make_book):
    book = make_book()

    response = client.delete(f"/books/{book.id}", headers=librarian_headers)

    assert response.status_code == 204
    assert client.get(f"/books/{book.id}", headers=librarian_headers).status_code == 404
    assert client.delete(f"/books/{book.id}", headers=librarian_headers).status_code == 404


def test_cannot_delete_book_with_active_loans(client, librarian_headers, make_book, make_user):
    book = make_book()
    loan = client.post("/loans", json={"book_id": book.id, "reader_id": make_user().id}, headers=librarian_headers)

    blocked = client.delete(f"/books/{book.id}", headers=librarian_headers)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "book_has_active_loans"

    client.post(f"/loans/{loan.json()['id']}/return", headers=librarian_headers)
    assert client.delete(f"/books/{book.id}", headers=librarian_headers).status_code == 204


def test_invalid_path_parameter_returns_422(client, reader_headers):
    assert client.get("/books/abc", headers=reader_headers).status_code == 422
    assert client.get("/books/0", headers=reader_headers).status_code == 422


def test_isbn_helper_generates_valid_isbns(client, librarian_headers):
    response = client.post("/books", json={**BOOK, "isbn": make_isbn(123)}, headers=librarian_headers)
    assert response.status_code == 201
