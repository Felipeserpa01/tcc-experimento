def test_create_book_as_librarian(client, librarian):
    resp = client.post(
        "/books/",
        json={
            "title": "O Hobbit",
            "author": "J.R.R. Tolkien",
            "isbn": "9780261102217",
            "year": 1937,
            "total_quantity": 3,
        },
        headers=librarian["headers"],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["available_quantity"] == 3
    assert data["total_quantity"] == 3


def test_create_book_as_reader_forbidden(client, reader):
    resp = client.post(
        "/books/",
        json={
            "title": "O Hobbit",
            "author": "J.R.R. Tolkien",
            "isbn": "9780261102217",
            "year": 1937,
            "total_quantity": 3,
        },
        headers=reader["headers"],
    )
    assert resp.status_code == 403


def test_create_book_requires_auth(client):
    resp = client.post(
        "/books/",
        json={
            "title": "O Hobbit",
            "author": "J.R.R. Tolkien",
            "isbn": "9780261102217",
            "year": 1937,
            "total_quantity": 3,
        },
    )
    assert resp.status_code == 401


def test_create_book_duplicate_isbn(client, librarian, sample_book):
    resp = client.post(
        "/books/",
        json={
            "title": "Outro Titulo",
            "author": "Outro Autor",
            "isbn": sample_book["isbn"],
            "year": 2020,
            "total_quantity": 1,
        },
        headers=librarian["headers"],
    )
    assert resp.status_code == 400


def test_create_book_invalid_isbn(client, librarian):
    resp = client.post(
        "/books/",
        json={
            "title": "Livro Invalido",
            "author": "Autor",
            "isbn": "123",
            "year": 2020,
            "total_quantity": 1,
        },
        headers=librarian["headers"],
    )
    assert resp.status_code == 422


def test_list_books(client, reader, sample_book):
    resp = client.get("/books/", headers=reader["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_search_books_by_title(client, reader, sample_book):
    resp = client.get("/books/", params={"search": "Clean"}, headers=reader["headers"])
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["title"] == "Clean Code"


def test_search_books_by_author(client, reader, sample_book):
    resp = client.get("/books/", params={"search": "Robert"}, headers=reader["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_search_books_no_match(client, reader, sample_book):
    resp = client.get("/books/", params={"search": "Inexistente"}, headers=reader["headers"])
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_book_not_found(client, reader):
    resp = client.get("/books/9999", headers=reader["headers"])
    assert resp.status_code == 404


def test_update_book(client, librarian, sample_book):
    resp = client.put(
        f"/books/{sample_book['id']}",
        json={"year": 2010},
        headers=librarian["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["year"] == 2010


def test_update_book_as_reader_forbidden(client, reader, sample_book):
    resp = client.put(
        f"/books/{sample_book['id']}",
        json={"year": 2010},
        headers=reader["headers"],
    )
    assert resp.status_code == 403


def test_update_book_increase_total_quantity_updates_available(client, librarian, sample_book):
    resp = client.put(
        f"/books/{sample_book['id']}",
        json={"total_quantity": 5},
        headers=librarian["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_quantity"] == 5
    assert data["available_quantity"] == 5


def test_update_book_reduce_total_below_active_loans_fails(
    client, librarian, reader, sample_book
):
    client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    resp = client.put(
        f"/books/{sample_book['id']}",
        json={"total_quantity": 1},
        headers=librarian["headers"],
    )
    assert resp.status_code == 400


def test_delete_book(client, librarian, sample_book):
    resp = client.delete(f"/books/{sample_book['id']}", headers=librarian["headers"])
    assert resp.status_code == 204

    resp = client.get(f"/books/{sample_book['id']}", headers=librarian["headers"])
    assert resp.status_code == 404


def test_delete_book_with_active_loan_fails(client, librarian, reader, sample_book):
    client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    resp = client.delete(f"/books/{sample_book['id']}", headers=librarian["headers"])
    assert resp.status_code == 400
