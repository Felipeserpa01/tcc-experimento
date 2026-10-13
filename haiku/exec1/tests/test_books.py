import pytest


def test_create_book_as_librarian(client, librarian_user, get_token):
    token = get_token("bibliotecario")
    response = client.post(
        "/api/books/",
        json={
            "title": "Harry Potter",
            "author": "J.K. Rowling",
            "isbn": "978-0439708180",
            "year": 1998,
            "total_quantity": 10,
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Harry Potter"
    assert data["author"] == "J.K. Rowling"
    assert data["available_quantity"] == 10


def test_create_book_as_reader_forbidden(client, reader_user, get_token):
    token = get_token("leitor")
    response = client.post(
        "/api/books/",
        json={
            "title": "Harry Potter",
            "author": "J.K. Rowling",
            "isbn": "978-0439708180",
            "year": 1998,
            "total_quantity": 10,
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_create_book_duplicate_isbn(client, librarian_user, get_token, sample_book):
    token = get_token("bibliotecario")
    response = client.post(
        "/api/books/",
        json={
            "title": "Different Title",
            "author": "Different Author",
            "isbn": "978-0451524935",
            "year": 2000,
            "total_quantity": 5,
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "já existe" in response.json()["detail"]


def test_list_books(client, reader_user, get_token, sample_book):
    token = get_token("leitor")
    response = client.get(
        "/api/books/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == "1984"


def test_get_book(client, reader_user, get_token, sample_book):
    token = get_token("leitor")
    response = client.get(
        f"/api/books/{sample_book.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "1984"


def test_get_nonexistent_book(client, reader_user, get_token):
    token = get_token("leitor")
    response = client.get(
        "/api/books/99999",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_update_book(client, librarian_user, get_token, sample_book):
    token = get_token("bibliotecario")
    response = client.put(
        f"/api/books/{sample_book.id}",
        json={
            "title": "1984 - Updated",
            "total_quantity": 8,
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "1984 - Updated"
    assert data["total_quantity"] == 8


def test_delete_book(client, librarian_user, get_token, sample_book):
    token = get_token("bibliotecario")
    response = client.delete(
        f"/api/books/{sample_book.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204


def test_search_by_title(client, reader_user, get_token, sample_book):
    token = get_token("leitor")
    response = client.get(
        "/api/books/search/by-title?title=1984",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["books"]) >= 1
    assert data["books"][0]["title"] == "1984"


def test_search_by_author(client, reader_user, get_token, sample_book):
    token = get_token("leitor")
    response = client.get(
        "/api/books/search/by-author?author=George",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["books"]) >= 1
