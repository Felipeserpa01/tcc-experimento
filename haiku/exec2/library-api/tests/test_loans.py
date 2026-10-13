import pytest
from datetime import datetime, timedelta


@pytest.fixture
def book_with_copies(librarian_token, client):
    response = client.post(
        "/books/",
        json={
            "title": "Test Book",
            "author": "Test Author",
            "isbn": "978-1234567890",
            "year": 2023,
            "total_quantity": 3
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    return response.json()["id"]


def test_borrow_book_success(client, reader_token, book_with_copies):
    response = client.post(
        "/loans/",
        json={"book_id": book_with_copies},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book_with_copies
    assert data["return_date"] is None


def test_borrow_nonexistent_book(client, reader_token):
    response = client.post(
        "/loans/",
        json={"book_id": 999},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 404
    assert "Book not found" in response.json()["detail"]


def test_borrow_no_available_copies(client, reader_token, librarian_token):
    book_response = client.post(
        "/books/",
        json={
            "title": "Limited Book",
            "author": "Author",
            "isbn": "978-0000000001",
            "year": 2023,
            "total_quantity": 1
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    book_id = book_response.json()["id"]

    reader2_response = client.post(
        "/auth/register",
        json={
            "email": "reader2@test.com",
            "full_name": "Reader 2",
            "password": "password123",
            "role": "reader"
        }
    )

    reader2_token = client.post(
        "/auth/login",
        json={"email": "reader2@test.com", "password": "password123"}
    ).json()["access_token"]

    client.post(
        "/loans/",
        json={"book_id": book_id},
        headers={"Authorization": f"Bearer {reader2_token}"}
    )

    response = client.post(
        "/loans/",
        json={"book_id": book_id},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 400
    assert "No copies available" in response.json()["detail"]


def test_borrow_librarian_cannot_borrow(client, librarian_token, book_with_copies):
    response = client.post(
        "/loans/",
        json={"book_id": book_with_copies},
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 403
    assert "Only readers can borrow" in response.json()["detail"]


def test_max_three_loans_limit(client, reader_token, librarian_token):
    books = []
    for i in range(4):
        response = client.post(
            "/books/",
            json={
                "title": f"Book {i+1}",
                "author": f"Author {i+1}",
                "isbn": f"978-{i:010d}",
                "year": 2023,
                "total_quantity": 1
            },
            headers={"Authorization": f"Bearer {librarian_token}"}
        )
        books.append(response.json()["id"])

    for i in range(3):
        response = client.post(
            "/loans/",
            json={"book_id": books[i]},
            headers={"Authorization": f"Bearer {reader_token}"}
        )
        assert response.status_code == 200

    response = client.post(
        "/loans/",
        json={"book_id": books[3]},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 400
    assert "cannot have more than 3 active loans" in response.json()["detail"]


def test_list_active_loans(client, reader_token, librarian_token, book_with_copies):
    client.post(
        "/loans/",
        json={"book_id": book_with_copies},
        headers={"Authorization": f"Bearer {reader_token}"}
    )

    response = client.get(
        "/loans/",
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["book_id"] == book_with_copies


def test_list_loans_only_reader(client, reader_token, librarian_token):
    response = client.get(
        "/loans/",
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 403
    assert "Only readers can list their loans" in response.json()["detail"]


def test_return_book_success(client, reader_token, book_with_copies):
    loan_response = client.post(
        "/loans/",
        json={"book_id": book_with_copies},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    loan_id = loan_response.json()["id"]

    return_date = datetime.utcnow() + timedelta(days=5)
    response = client.post(
        f"/loans/{loan_id}/return",
        json={"return_date": return_date.isoformat()},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["return_date"] is not None
    assert data["fine"] == 0.0


def test_return_book_with_fine(client, reader_token, book_with_copies):
    loan_response = client.post(
        "/loans/",
        json={"book_id": book_with_copies},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    loan_data = loan_response.json()
    loan_id = loan_data["id"]

    due_date = datetime.fromisoformat(loan_data["due_date"])
    return_date = due_date + timedelta(days=5)
    response = client.post(
        f"/loans/{loan_id}/return",
        json={"return_date": return_date.isoformat()},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fine"] > 0
    assert data["fine"] == 25.0


def test_return_nonexistent_loan(client, reader_token):
    return_date = datetime.utcnow().isoformat()
    response = client.post(
        "/loans/999/return",
        json={"return_date": return_date},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 404
    assert "Loan not found" in response.json()["detail"]


def test_return_already_returned_book(client, reader_token, book_with_copies):
    loan_response = client.post(
        "/loans/",
        json={"book_id": book_with_copies},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    loan_id = loan_response.json()["id"]

    return_date = datetime.utcnow().isoformat()
    client.post(
        f"/loans/{loan_id}/return",
        json={"return_date": return_date},
        headers={"Authorization": f"Bearer {reader_token}"}
    )

    response = client.post(
        f"/loans/{loan_id}/return",
        json={"return_date": return_date},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 400
    assert "already been returned" in response.json()["detail"]


def test_librarian_can_process_return(client, reader_token, librarian_token, book_with_copies):
    loan_response = client.post(
        "/loans/",
        json={"book_id": book_with_copies},
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    loan_id = loan_response.json()["id"]

    return_date = datetime.utcnow().isoformat()
    response = client.post(
        f"/loans/{loan_id}/return",
        json={"return_date": return_date},
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 200


def test_reader_cannot_return_others_loan(client, librarian_token):
    reader1_response = client.post(
        "/auth/register",
        json={
            "email": "reader1@test.com",
            "full_name": "Reader 1",
            "password": "password123",
            "role": "reader"
        }
    )

    reader2_response = client.post(
        "/auth/register",
        json={
            "email": "reader2@test.com",
            "full_name": "Reader 2",
            "password": "password123",
            "role": "reader"
        }
    )

    reader1_token = client.post(
        "/auth/login",
        json={"email": "reader1@test.com", "password": "password123"}
    ).json()["access_token"]

    reader2_token = client.post(
        "/auth/login",
        json={"email": "reader2@test.com", "password": "password123"}
    ).json()["access_token"]

    book_response = client.post(
        "/books/",
        json={
            "title": "Test Book",
            "author": "Test Author",
            "isbn": "978-1234567890",
            "year": 2023,
            "total_quantity": 2
        },
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    book_id = book_response.json()["id"]

    loan_response = client.post(
        "/loans/",
        json={"book_id": book_id},
        headers={"Authorization": f"Bearer {reader1_token}"}
    )
    loan_id = loan_response.json()["id"]

    return_date = datetime.utcnow().isoformat()
    response = client.post(
        f"/loans/{loan_id}/return",
        json={"return_date": return_date},
        headers={"Authorization": f"Bearer {reader2_token}"}
    )
    assert response.status_code == 403
    assert "can only return your own loans" in response.json()["detail"]
