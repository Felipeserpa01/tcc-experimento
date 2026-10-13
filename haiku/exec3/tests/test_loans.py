import pytest
from fastapi import status
from datetime import datetime, timedelta

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

def get_reader_token(client, username="reader123"):
    client.post(
        "/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "Password123",
            "user_type": "reader"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": "Password123"
        }
    )
    return response.json()["access_token"]

def create_test_book(client, lib_token, isbn="978-3-16-148410-0", total_qty=5, title="Test Book"):
    response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {lib_token}"},
        json={
            "title": title,
            "author": "Test Author",
            "isbn": isbn,
            "year": 2023,
            "total_quantity": total_qty
        }
    )
    assert response.status_code == 201, f"Failed to create book: {response.json()}"
    return response.json()["id"]

def test_create_loan_success(client):
    lib_token = get_librarian_token(client)
    reader_token = get_reader_token(client)

    book_id = create_test_book(client, lib_token)

    response = client.post(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"book_id": book_id}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "active"
    assert data["fine_amount"] == 0.0

def test_create_loan_book_not_available(client):
    lib_token = get_librarian_token(client)
    reader_token = get_reader_token(client)

    book_id = create_test_book(client, lib_token, total_qty=1)

    client.post(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"book_id": book_id}
    )

    response = client.post(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"book_id": book_id}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_create_loan_max_loans_exceeded(client):
    lib_token = get_librarian_token(client)
    reader_token = get_reader_token(client)

    for i in range(4):
        book_id = create_test_book(
            client, lib_token,
            isbn=f"978-3-16-14841{i}-{i}",
            total_qty=1,
            title=f"Book {i}"
        )
        client.post(
            "/loans/",
            headers={"Authorization": f"Bearer {reader_token}"},
            json={"book_id": book_id}
        )

    book_id_5 = create_test_book(
        client, lib_token,
        isbn="978-0-13-293-5",
        total_qty=1,
        title="Book 5"
    )

    response = client.post(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"book_id": book_id_5}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_return_loan_on_time(client):
    lib_token = get_librarian_token(client)
    reader_token = get_reader_token(client)

    book_id = create_test_book(client, lib_token)

    loan_response = client.post(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"book_id": book_id}
    )
    loan_id = loan_response.json()["id"]

    response = client.post(
        "/loans/return",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"loan_id": loan_id}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "returned"
    assert data["fine_amount"] == 0.0
    assert data["return_date"] is not None

def test_return_loan_overdue(client):
    lib_token = get_librarian_token(client)
    reader_token = get_reader_token(client)

    book_id = create_test_book(client, lib_token)

    loan_response = client.post(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"book_id": book_id}
    )
    loan_id = loan_response.json()["id"]

    response = client.post(
        "/loans/return",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"loan_id": loan_id}
    )

    data = response.json()
    assert response.status_code == status.HTTP_200_OK

def test_get_active_loans(client):
    lib_token = get_librarian_token(client)
    reader_token = get_reader_token(client)

    book_id_1 = create_test_book(client, lib_token, isbn="978-3-16-148410-0")
    book_id_2 = create_test_book(client, lib_token, isbn="978-3-16-148410-1")

    client.post(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"book_id": book_id_1}
    )

    client.post(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"book_id": book_id_2}
    )

    response = client.get(
        "/loans/user/active",
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2

def test_get_loan_unauthorized(client):
    lib_token = get_librarian_token(client)
    reader_token_1 = get_reader_token(client, "reader1")
    reader_token_2 = get_reader_token(client, "reader2")

    book_id = create_test_book(client, lib_token)

    loan_response = client.post(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token_1}"},
        json={"book_id": book_id}
    )
    loan_id = loan_response.json()["id"]

    response = client.get(
        f"/loans/{loan_id}",
        headers={"Authorization": f"Bearer {reader_token_2}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_return_loan_not_found(client):
    reader_token = get_reader_token(client)

    response = client.post(
        "/loans/return",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"loan_id": 9999}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_book_availability_updated_on_loan(client):
    lib_token = get_librarian_token(client)
    reader_token = get_reader_token(client)

    book_id = create_test_book(client, lib_token, total_qty=5)

    book_before = client.get(f"/books/{book_id}").json()
    assert book_before["available_quantity"] == 5

    client.post(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"book_id": book_id}
    )

    book_after = client.get(f"/books/{book_id}").json()
    assert book_after["available_quantity"] == 4

def test_book_availability_restored_on_return(client):
    lib_token = get_librarian_token(client)
    reader_token = get_reader_token(client)

    book_id = create_test_book(client, lib_token, total_qty=5)

    loan_response = client.post(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"book_id": book_id}
    )
    loan_id = loan_response.json()["id"]

    book_borrowed = client.get(f"/books/{book_id}").json()
    assert book_borrowed["available_quantity"] == 4

    client.post(
        "/loans/return",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"loan_id": loan_id}
    )

    book_returned = client.get(f"/books/{book_id}").json()
    assert book_returned["available_quantity"] == 5
