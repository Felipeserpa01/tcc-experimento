import pytest
from datetime import datetime, timezone, timedelta


def test_create_loan(client, reader_user, get_token, sample_book):
    token = get_token("leitor")
    response = client.post(
        "/api/loans/",
        json={"book_id": sample_book.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == reader_user.id
    assert data["book_id"] == sample_book.id
    assert data["return_date"] is None
    assert data["fine"] == 0.0


def test_create_loan_unavailable_book(client, reader_user, get_token, sample_book, db):
    sample_book.available_quantity = 0
    db.commit()

    token = get_token("leitor")
    response = client.post(
        "/api/loans/",
        json={"book_id": sample_book.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "exemplar disponível" in response.json()["detail"]


def test_create_loan_nonexistent_book(client, reader_user, get_token):
    token = get_token("leitor")
    response = client.post(
        "/api/loans/",
        json={"book_id": 99999},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_max_loans_per_user(client, reader_user, get_token, sample_book, db):
    from app.models import Book

    token = get_token("leitor")

    for i in range(3):
        book = Book(
            title=f"Book {i}",
            author=f"Author {i}",
            isbn=f"isbn-{i}",
            year=2000,
            total_quantity=5,
            available_quantity=5,
        )
        db.add(book)
    db.commit()

    books = db.query(Book).filter(Book.title.like("Book %")).all()

    for book in books:
        response = client.post(
            "/api/loans/",
            json={"book_id": book.id},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201

    response = client.post(
        "/api/loans/",
        json={"book_id": sample_book.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "Limite" in response.json()["detail"]


def test_return_loan(client, reader_user, get_token, sample_book, db):
    from app.models import Loan

    token = get_token("leitor")

    response = client.post(
        "/api/loans/",
        json={"book_id": sample_book.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    loan_id = response.json()["id"]

    return_date = datetime.now(timezone.utc)
    response = client.post(
        f"/api/loans/{loan_id}/return",
        json={"return_date": return_date.isoformat()},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["return_date"] is not None


def test_return_loan_late(client, reader_user, get_token, sample_book, db):
    from app.models import Loan

    token = get_token("leitor")

    response = client.post(
        "/api/loans/",
        json={"book_id": sample_book.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    loan_id = response.json()["id"]

    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    return_date = loan.due_date + timedelta(days=5)

    response = client.post(
        f"/api/loans/{loan_id}/return",
        json={"return_date": return_date.isoformat()},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fine"] == 25.0


def test_return_already_returned_loan(client, reader_user, get_token, sample_book):
    token = get_token("leitor")

    response = client.post(
        "/api/loans/",
        json={"book_id": sample_book.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    loan_id = response.json()["id"]

    return_date = datetime.now(timezone.utc)
    client.post(
        f"/api/loans/{loan_id}/return",
        json={"return_date": return_date.isoformat()},
        headers={"Authorization": f"Bearer {token}"}
    )

    response = client.post(
        f"/api/loans/{loan_id}/return",
        json={"return_date": return_date.isoformat()},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "já foi devolvido" in response.json()["detail"]


def test_get_my_loans(client, reader_user, get_token, sample_book):
    token = get_token("leitor")

    client.post(
        "/api/loans/",
        json={"book_id": sample_book.id},
        headers={"Authorization": f"Bearer {token}"}
    )

    response = client.get(
        "/api/loans/my-loans",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_active_loans(client, reader_user, librarian_user, get_token, sample_book):
    reader_token = get_token("leitor")

    client.post(
        "/api/loans/",
        json={"book_id": sample_book.id},
        headers={"Authorization": f"Bearer {reader_token}"}
    )

    librarian_token = get_token("bibliotecario")
    response = client.get(
        f"/api/loans/active-loans/{reader_user.id}",
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_loan(client, reader_user, get_token, sample_book):
    token = get_token("leitor")

    response = client.post(
        "/api/loans/",
        json={"book_id": sample_book.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    loan_id = response.json()["id"]

    response = client.get(
        f"/api/loans/{loan_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == loan_id


def test_list_all_loans_as_librarian(client, librarian_user, get_token, sample_book):
    librarian_token = get_token("bibliotecario")

    response = client.get(
        "/api/loans/",
        headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 200


def test_list_all_loans_as_reader_forbidden(client, reader_user, get_token):
    reader_token = get_token("leitor")

    response = client.get(
        "/api/loans/",
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 403
