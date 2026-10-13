import pytest

from tests.conftest import make_isbn13

BOOK = {
    "title": "Dom Casmurro",
    "author": "Machado de Assis",
    "isbn": "978-0-13-235088-4",
    "year": 1899,
    "total_quantity": 3,
}


class TestCreateBook:
    def test_librarian_creates_book(self, client, librarian_headers):
        response = client.post("/books", json=BOOK, headers=librarian_headers)

        assert response.status_code == 201
        body = response.json()
        assert body["isbn"] == "9780132350884"
        assert body["total_quantity"] == 3
        assert body["available_quantity"] == 3

    def test_reader_cannot_create_book(self, client, reader_headers):
        response = client.post("/books", json=BOOK, headers=reader_headers)

        assert response.status_code == 403
        assert response.json()["code"] == "librarian_required"

    def test_unauthenticated_cannot_create_book(self, client):
        assert client.post("/books", json=BOOK).status_code == 401

    def test_duplicate_isbn_returns_409(self, client, librarian_headers):
        client.post("/books", json=BOOK, headers=librarian_headers)
        response = client.post("/books", json={**BOOK, "isbn": "9780132350884"}, headers=librarian_headers)

        assert response.status_code == 409
        assert response.json()["code"] == "isbn_already_registered"

    @pytest.mark.parametrize(
        ("override", "field"),
        [
            ({"isbn": "9780132350885"}, "isbn"),
            ({"title": ""}, "title"),
            ({"year": 3000}, "year"),
            ({"total_quantity": 0}, "total_quantity"),
            ({"total_quantity": "muitos"}, "total_quantity"),
        ],
    )
    def test_invalid_data_returns_422(self, client, librarian_headers, override, field):
        response = client.post("/books", json={**BOOK, **override}, headers=librarian_headers)

        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"][-1] == field

    def test_missing_fields_return_422(self, client, librarian_headers):
        response = client.post("/books", json={"title": "Só título"}, headers=librarian_headers)
        assert response.status_code == 422


class TestReadAndSearchBooks:
    @pytest.fixture(autouse=True)
    def catalog(self, book_factory):
        book_factory(title="Dom Casmurro", author="Machado de Assis")
        book_factory(title="Quincas Borba", author="Machado de Assis", total_quantity=1)
        book_factory(title="O Cortiço", author="Aluísio Azevedo")

    def test_list_all_books_sorted_by_title(self, client, reader_headers):
        response = client.get("/books", headers=reader_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert [b["title"] for b in body["items"]] == ["Dom Casmurro", "O Cortiço", "Quincas Borba"]

    def test_search_by_title(self, client, reader_headers):
        body = client.get("/books", params={"title": "cortiço"}, headers=reader_headers).json()
        assert [b["title"] for b in body["items"]] == ["O Cortiço"]

    def test_search_by_author(self, client, reader_headers):
        body = client.get("/books", params={"author": "MACHADO"}, headers=reader_headers).json()
        assert body["total"] == 2

    def test_search_by_title_or_author(self, client, reader_headers):
        by_author = client.get("/books", params={"q": "azevedo"}, headers=reader_headers).json()
        by_title = client.get("/books", params={"q": "borba"}, headers=reader_headers).json()
        assert by_author["items"][0]["title"] == "O Cortiço"
        assert by_title["items"][0]["title"] == "Quincas Borba"

    def test_filter_only_available_books(self, client, librarian_headers, reader):
        quincas = client.get("/books", params={"title": "quincas"}, headers=librarian_headers).json()["items"][0]
        client.post("/loans", json={"book_id": quincas["id"], "reader_id": reader.id}, headers=librarian_headers)

        body = client.get("/books", params={"available_only": True}, headers=librarian_headers).json()

        assert body["total"] == 2
        assert "Quincas Borba" not in {b["title"] for b in body["items"]}

    def test_search_without_results(self, client, reader_headers):
        body = client.get("/books", params={"q": "inexistente"}, headers=reader_headers).json()
        assert body == {"items": [], "total": 0, "skip": 0, "limit": 20}

    def test_pagination(self, client, reader_headers):
        body = client.get("/books", params={"skip": 2, "limit": 2}, headers=reader_headers).json()
        assert body["total"] == 3
        assert len(body["items"]) == 1

    def test_invalid_pagination_returns_422(self, client, reader_headers):
        assert client.get("/books", params={"limit": 1000}, headers=reader_headers).status_code == 422

    def test_get_book_by_id(self, client, reader_headers, book_factory):
        book = book_factory(title="Capitães da Areia")
        response = client.get(f"/books/{book.id}", headers=reader_headers)

        assert response.status_code == 200
        assert response.json()["title"] == "Capitães da Areia"

    def test_unknown_book_returns_404(self, client, reader_headers):
        response = client.get("/books/999", headers=reader_headers)

        assert response.status_code == 404
        assert response.json() == {"detail": "Livro não encontrado", "code": "book_not_found"}


class TestUpdateBook:
    def test_partial_update(self, client, librarian_headers, book_factory):
        book = book_factory(title="Titulo errado", year=2000)

        response = client.patch(f"/books/{book.id}", json={"title": "Título correto"}, headers=librarian_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Título correto"
        assert body["year"] == 2000

    def test_update_total_quantity_adjusts_available(self, client, librarian_headers, book_factory, reader):
        book = book_factory(total_quantity=2)
        client.post("/loans", json={"book_id": book.id, "reader_id": reader.id}, headers=librarian_headers)

        response = client.patch(f"/books/{book.id}", json={"total_quantity": 4}, headers=librarian_headers)

        assert response.status_code == 200
        assert response.json()["available_quantity"] == 3

    def test_total_below_loaned_returns_409(self, client, librarian_headers, book_factory, reader, other_reader):
        book = book_factory(total_quantity=3)
        for r in (reader, other_reader):
            client.post("/loans", json={"book_id": book.id, "reader_id": r.id}, headers=librarian_headers)

        response = client.patch(f"/books/{book.id}", json={"total_quantity": 1}, headers=librarian_headers)

        assert response.status_code == 409
        assert response.json()["code"] == "total_below_loaned"

    def test_null_field_returns_422(self, client, librarian_headers, book_factory):
        book = book_factory()
        response = client.patch(f"/books/{book.id}", json={"title": None}, headers=librarian_headers)
        assert response.status_code == 422

    def test_isbn_conflict_returns_409(self, client, librarian_headers, book_factory):
        first, second = book_factory(isbn=make_isbn13(100)), book_factory(isbn=make_isbn13(200))
        response = client.patch(f"/books/{second.id}", json={"isbn": first.isbn}, headers=librarian_headers)
        assert response.status_code == 409

    def test_reader_cannot_update(self, client, reader_headers, book_factory):
        book = book_factory()
        assert client.patch(f"/books/{book.id}", json={"title": "X"}, headers=reader_headers).status_code == 403

    def test_unknown_book_returns_404(self, client, librarian_headers):
        assert client.patch("/books/999", json={"title": "X"}, headers=librarian_headers).status_code == 404


class TestDeleteBook:
    def test_delete_book(self, client, librarian_headers, book_factory):
        book = book_factory()

        response = client.delete(f"/books/{book.id}", headers=librarian_headers)

        assert response.status_code == 204
        assert client.get(f"/books/{book.id}", headers=librarian_headers).status_code == 404

    def test_book_with_active_loans_cannot_be_deleted(self, client, librarian_headers, book_factory, reader):
        book = book_factory()
        client.post("/loans", json={"book_id": book.id, "reader_id": reader.id}, headers=librarian_headers)

        response = client.delete(f"/books/{book.id}", headers=librarian_headers)

        assert response.status_code == 409
        assert response.json()["code"] == "book_has_active_loans"

    def test_reader_cannot_delete(self, client, reader_headers, book_factory):
        book = book_factory()
        assert client.delete(f"/books/{book.id}", headers=reader_headers).status_code == 403

    def test_unknown_book_returns_404(self, client, librarian_headers):
        assert client.delete("/books/999", headers=librarian_headers).status_code == 404
