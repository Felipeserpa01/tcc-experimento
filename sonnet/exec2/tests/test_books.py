def create_book(client, headers, **overrides):
    payload = {
        "title": "Dom Casmurro",
        "author": "Machado de Assis",
        "isbn": "978-8535910663",
        "year": 1899,
        "total_copies": 3,
    }
    payload.update(overrides)
    return client.post("/books/", json=payload, headers=headers)


def test_librarian_can_create_book(client, librarian):
    response = create_book(client, librarian["headers"])
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Dom Casmurro"
    assert data["total_copies"] == 3
    assert data["available_copies"] == 3


def test_reader_cannot_create_book(client, reader):
    response = create_book(client, reader["headers"])
    assert response.status_code == 403


def test_create_book_duplicate_isbn_fails(client, librarian):
    create_book(client, librarian["headers"])
    response = create_book(client, librarian["headers"], title="Outro Titulo")
    assert response.status_code == 409


def test_list_books(client, librarian, reader):
    create_book(client, librarian["headers"])
    create_book(client, librarian["headers"], title="Memorias Postumas", isbn="978-0000000001")

    response = client.get("/books/", headers=reader["headers"])
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_books_by_title(client, librarian):
    create_book(client, librarian["headers"])
    create_book(client, librarian["headers"], title="Memorias Postumas", isbn="978-0000000001")

    response = client.get("/books/?q=Casmurro", headers=librarian["headers"])
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["title"] == "Dom Casmurro"


def test_search_books_by_author(client, librarian):
    create_book(client, librarian["headers"])
    create_book(
        client,
        librarian["headers"],
        title="Grande Sertao: Veredas",
        author="Guimaraes Rosa",
        isbn="978-0000000001",
    )

    response = client.get("/books/?q=Machado", headers=librarian["headers"])
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["author"] == "Machado de Assis"


def test_get_book_not_found(client, librarian):
    response = client.get("/books/999", headers=librarian["headers"])
    assert response.status_code == 404


def test_librarian_can_update_book(client, librarian):
    created = create_book(client, librarian["headers"]).json()
    response = client.put(
        f"/books/{created['id']}",
        json={"year": 1900},
        headers=librarian["headers"],
    )
    assert response.status_code == 200
    assert response.json()["year"] == 1900


def test_reader_cannot_update_book(client, librarian, reader):
    created = create_book(client, librarian["headers"]).json()
    response = client.put(
        f"/books/{created['id']}",
        json={"year": 1900},
        headers=reader["headers"],
    )
    assert response.status_code == 403


def test_librarian_can_delete_book_without_active_loans(client, librarian):
    created = create_book(client, librarian["headers"]).json()
    response = client.delete(f"/books/{created['id']}", headers=librarian["headers"])
    assert response.status_code == 204

    get_response = client.get(f"/books/{created['id']}", headers=librarian["headers"])
    assert get_response.status_code == 404


def test_cannot_delete_book_with_active_loans(client, librarian, reader):
    created = create_book(client, librarian["headers"], total_copies=1).json()
    client.post(
        "/loans/",
        json={"book_id": created["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    response = client.delete(f"/books/{created['id']}", headers=librarian["headers"])
    assert response.status_code == 400
