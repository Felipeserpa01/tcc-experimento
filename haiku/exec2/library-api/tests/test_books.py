import pytest


def test_create_book_as_librarian(client, librarian_token):
    response = client.post(
        "/books/",
        json={
            "title": "Python Basics",
            "author": "John Doe",
            "isbn": "978-1234567890",
            "year": 2023,
            "total_quantity": 5
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Python Basics"
    assert data["author"] == "John Doe"
    assert data["total_quantity"] == 5
    assert data["available_quantity"] == 5


def test_create_book_as_reader_forbidden(client, reader_token):
    response = client.post(
        "/books/",
        json={
            "title": "Python Basics",
            "author": "John Doe",
            "isbn": "978-1234567890",
            "year": 2023,
            "total_quantity": 5
        },
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 403
    assert "Only librarians" in response.json()["detail"]


def test_create_book_duplicate_isbn(client, librarian_token):
    isbn = "978-1234567890"
    client.post(
        "/books/",
        json={
            "title": "Python Basics",
            "author": "John Doe",
            "isbn": isbn,
            "year": 2023,
            "total_quantity": 5
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )

    response = client.post(
        "/books/",
        json={
            "title": "Another Book",
            "author": "Jane Doe",
            "isbn": isbn,
            "year": 2024,
            "total_quantity": 3
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 400
    assert "ISBN already exists" in response.json()["detail"]


def test_list_books(client, reader_token, librarian_token):
    for i in range(3):
        client.post(
            "/books/",
            json={
                "title": f"Book {i+1}",
                "author": f"Author {i+1}",
                "isbn": f"978-123456789{i}",
                "year": 2023 + i,
                "total_quantity": 5
            },
            headers={"Authorization": f"Bearer {librarian_token}"}
        )

    response = client.get(
        "/books/",
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_list_books_pagination(client, reader_token, librarian_token):
    for i in range(15):
        client.post(
            "/books/",
            json={
                "title": f"Book {i+1}",
                "author": f"Author {i+1}",
                "isbn": f"978-{i:010d}",
                "year": 2023,
                "total_quantity": 5
            },
            headers={"Authorization": f"Bearer {librarian_token}"}
        )

    response = client.get(
        "/books/?skip=0&limit=10",
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10


def test_search_books_by_title(client, reader_token, librarian_token):
    client.post(
        "/books/",
        json={
            "title": "Python Advanced",
            "author": "John Doe",
            "isbn": "978-1234567890",
            "year": 2023,
            "total_quantity": 5
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )

    response = client.get(
        "/books/search?q=Python",
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Python Advanced"


def test_search_books_by_author(client, reader_token, librarian_token):
    client.post(
        "/books/",
        json={
            "title": "Python Advanced",
            "author": "John Doe",
            "isbn": "978-1234567890",
            "year": 2023,
            "total_quantity": 5
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )

    response = client.get(
        "/books/search?q=John",
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["author"] == "John Doe"


def test_get_book_detail(client, reader_token, librarian_token):
    create_response = client.post(
        "/books/",
        json={
            "title": "Python Basics",
            "author": "John Doe",
            "isbn": "978-1234567890",
            "year": 2023,
            "total_quantity": 5
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    book_id = create_response.json()["id"]

    response = client.get(
        f"/books/{book_id}",
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Python Basics"


def test_get_book_not_found(client, reader_token):
    response = client.get(
        "/books/999",
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 404


def test_update_book(client, librarian_token):
    create_response = client.post(
        "/books/",
        json={
            "title": "Python Basics",
            "author": "John Doe",
            "isbn": "978-1234567890",
            "year": 2023,
            "total_quantity": 5
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    book_id = create_response.json()["id"]

    response = client.put(
        f"/books/{book_id}",
        json={
            "title": "Python Advanced",
            "year": 2024
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Python Advanced"
    assert data["year"] == 2024


def test_delete_book(client, librarian_token):
    create_response = client.post(
        "/books/",
        json={
            "title": "Python Basics",
            "author": "John Doe",
            "isbn": "978-1234567890",
            "year": 2023,
            "total_quantity": 5
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    book_id = create_response.json()["id"]

    response = client.delete(
        f"/books/{book_id}",
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 200

    get_response = client.get(
        f"/books/{book_id}",
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert get_response.status_code == 404
