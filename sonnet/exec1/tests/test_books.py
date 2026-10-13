from tests.conftest import auth_headers


def create_book(client, token, **overrides):
    payload = {
        "title": "Dom Casmurro",
        "author": "Machado de Assis",
        "isbn": "9788535910663",
        "year": 1899,
        "total_quantity": 3,
    }
    payload.update(overrides)
    return client.post("/books/", json=payload, headers=auth_headers(token))


def test_librarian_can_create_book(client, librarian_token):
    response = create_book(client, librarian_token)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Dom Casmurro"
    assert body["total_quantity"] == 3
    assert body["available_quantity"] == 3


def test_reader_cannot_create_book(client, reader_token_and_id):
    reader_token, _ = reader_token_and_id
    response = create_book(client, reader_token)
    assert response.status_code == 403


def test_create_book_requires_authentication(client):
    response = client.post(
        "/books/",
        json={
            "title": "X",
            "author": "Y",
            "isbn": "9788535910663",
            "year": 2000,
            "total_quantity": 1,
        },
    )
    assert response.status_code == 401


def test_duplicate_isbn_rejected(client, librarian_token):
    create_book(client, librarian_token)
    response = create_book(client, librarian_token, title="Another Title")
    assert response.status_code == 409


def test_invalid_isbn_rejected(client, librarian_token):
    response = create_book(client, librarian_token, isbn="not-an-isbn")
    assert response.status_code == 422


def test_invalid_year_rejected(client, librarian_token):
    response = create_book(client, librarian_token, year=3000)
    assert response.status_code == 422


def test_list_books(client, librarian_token):
    create_book(client, librarian_token)
    create_book(client, librarian_token, isbn="9780132350884", title="Clean Code", author="Robert C. Martin")

    response = client.get("/books/", headers=auth_headers(librarian_token))
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_books_by_title(client, librarian_token):
    create_book(client, librarian_token)
    create_book(client, librarian_token, isbn="9780132350884", title="Clean Code", author="Robert C. Martin")

    response = client.get("/books/?title=clean", headers=auth_headers(librarian_token))
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["title"] == "Clean Code"


def test_search_books_by_author(client, librarian_token):
    create_book(client, librarian_token)
    create_book(client, librarian_token, isbn="9780132350884", title="Clean Code", author="Robert C. Martin")

    response = client.get("/books/?author=machado", headers=auth_headers(librarian_token))
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["author"] == "Machado de Assis"


def test_get_book_not_found(client, librarian_token):
    response = client.get("/books/999", headers=auth_headers(librarian_token))
    assert response.status_code == 404


def test_librarian_can_update_book(client, librarian_token):
    created = create_book(client, librarian_token).json()
    response = client.put(
        f"/books/{created['id']}",
        json={"title": "Dom Casmurro (edição revisada)"},
        headers=auth_headers(librarian_token),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Dom Casmurro (edição revisada)"


def test_reader_cannot_update_book(client, librarian_token, reader_token_and_id):
    reader_token, _ = reader_token_and_id
    created = create_book(client, librarian_token).json()
    response = client.put(
        f"/books/{created['id']}",
        json={"title": "Hacked"},
        headers=auth_headers(reader_token),
    )
    assert response.status_code == 403


def test_update_total_quantity_adjusts_available(client, librarian_token):
    created = create_book(client, librarian_token, total_quantity=5).json()
    response = client.put(
        f"/books/{created['id']}",
        json={"total_quantity": 10},
        headers=auth_headers(librarian_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_quantity"] == 10
    assert body["available_quantity"] == 10


def test_librarian_can_delete_book(client, librarian_token):
    created = create_book(client, librarian_token).json()
    response = client.delete(f"/books/{created['id']}", headers=auth_headers(librarian_token))
    assert response.status_code == 204

    get_response = client.get(f"/books/{created['id']}", headers=auth_headers(librarian_token))
    assert get_response.status_code == 404


def test_reader_cannot_delete_book(client, librarian_token, reader_token_and_id):
    reader_token, _ = reader_token_and_id
    created = create_book(client, librarian_token).json()
    response = client.delete(f"/books/{created['id']}", headers=auth_headers(reader_token))
    assert response.status_code == 403
