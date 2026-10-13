import pytest
from fastapi import status

def get_librarian_token(client):
    client.post(
        "/auth/register",
        json={
            "username": "librarian123",
            "email": "librarian@example.com",
            "password": "Password123",
            "user_type": "librarian"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "username": "librarian123",
            "password": "Password123"
        }
    )
    return response.json()["access_token"]

def get_reader_token(client):
    client.post(
        "/auth/register",
        json={
            "username": "reader123",
            "email": "reader@example.com",
            "password": "Password123",
            "user_type": "reader"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "username": "reader123",
            "password": "Password123"
        }
    )
    return response.json()["access_token"]

def test_create_book_success(client):
    token = get_librarian_token(client)

    response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Book",
            "author": "Test Author",
            "isbn": "978-3-16-148410-0",
            "year": 2023,
            "total_quantity": 5,
            "description": "A test book"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Test Book"
    assert data["available_quantity"] == 5

def test_create_book_invalid_isbn(client):
    token = get_librarian_token(client)

    response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Book",
            "author": "Test Author",
            "isbn": "invalid-isbn",
            "year": 2023,
            "total_quantity": 5
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_create_book_duplicate_isbn(client):
    token = get_librarian_token(client)

    client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Book",
            "author": "Test Author",
            "isbn": "978-3-16-148410-0",
            "year": 2023,
            "total_quantity": 5
        }
    )

    response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Another Book",
            "author": "Another Author",
            "isbn": "978-3-16-148410-0",
            "year": 2023,
            "total_quantity": 3
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_create_book_reader_cannot(client):
    token = get_reader_token(client)

    response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Book",
            "author": "Test Author",
            "isbn": "978-3-16-148410-0",
            "year": 2023,
            "total_quantity": 5
        }
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_list_books(client):
    token = get_librarian_token(client)

    client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Book 1",
            "author": "Author 1",
            "isbn": "978-3-16-148410-0",
            "year": 2023,
            "total_quantity": 5
        }
    )

    client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Book 2",
            "author": "Author 2",
            "isbn": "978-3-16-148410-1",
            "year": 2023,
            "total_quantity": 3
        }
    )

    response = client.get("/books/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2

def test_search_books_by_title(client):
    token = get_librarian_token(client)

    client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Python Programming",
            "author": "Author 1",
            "isbn": "978-3-16-148410-0",
            "year": 2023,
            "total_quantity": 5
        }
    )

    response = client.get("/books/search?title=Python")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Python Programming"

def test_search_books_by_author(client):
    token = get_librarian_token(client)

    client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Book 1",
            "author": "John Doe",
            "isbn": "978-3-16-148410-0",
            "year": 2023,
            "total_quantity": 5
        }
    )

    response = client.get("/books/search?author=John")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1

def test_get_book(client):
    token = get_librarian_token(client)

    create_response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Book",
            "author": "Test Author",
            "isbn": "978-3-16-148410-0",
            "year": 2023,
            "total_quantity": 5
        }
    )
    book_id = create_response.json()["id"]

    response = client.get(f"/books/{book_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "Test Book"

def test_get_nonexistent_book(client):
    response = client.get("/books/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_update_book(client):
    token = get_librarian_token(client)

    create_response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Book",
            "author": "Test Author",
            "isbn": "978-3-16-148410-0",
            "year": 2023,
            "total_quantity": 5
        }
    )
    book_id = create_response.json()["id"]

    response = client.put(
        f"/books/{book_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Updated Title",
            "year": 2024
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["year"] == 2024

def test_delete_book(client):
    token = get_librarian_token(client)

    create_response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Book",
            "author": "Test Author",
            "isbn": "978-3-16-148410-0",
            "year": 2023,
            "total_quantity": 5
        }
    )
    book_id = create_response.json()["id"]

    response = client.delete(
        f"/books/{book_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(f"/books/{book_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
