from datetime import date, timedelta

from app.models import Loan
from tests.conftest import auth_headers, login, register_user


def create_book(client, token, **overrides):
    payload = {
        "title": "Dom Casmurro",
        "author": "Machado de Assis",
        "isbn": "9788535910663",
        "year": 1899,
        "total_quantity": 2,
    }
    payload.update(overrides)
    return client.post("/books/", json=payload, headers=auth_headers(token)).json()


def test_librarian_can_register_loan(client, librarian_token, reader_token_and_id):
    _, reader_id = reader_token_and_id
    book = create_book(client, librarian_token)

    response = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader_id},
        headers=auth_headers(librarian_token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["book_id"] == book["id"]
    assert body["reader_id"] == reader_id
    assert body["return_date"] is None
    assert body["fine_amount"] is None

    book_after = client.get(f"/books/{book['id']}", headers=auth_headers(librarian_token)).json()
    assert book_after["available_quantity"] == 1


def test_reader_cannot_register_loan(client, librarian_token, reader_token_and_id):
    reader_token, reader_id = reader_token_and_id
    book = create_book(client, librarian_token)

    response = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader_id},
        headers=auth_headers(reader_token),
    )
    assert response.status_code == 403


def test_cannot_loan_book_with_no_available_copies(client, librarian_token, reader_token_and_id):
    _, reader_id = reader_token_and_id
    book = create_book(client, librarian_token, total_quantity=1)

    first = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader_id},
        headers=auth_headers(librarian_token),
    )
    assert first.status_code == 201

    other_reader = register_user(client, "reader2", "reader2@example.com", "senha123", "leitor")

    second = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": other_reader["id"]},
        headers=auth_headers(librarian_token),
    )
    assert second.status_code == 400
    assert "available" in second.json()["detail"].lower()


def test_reader_limited_to_three_simultaneous_loans(client, librarian_token, reader_token_and_id):
    _, reader_id = reader_token_and_id

    for i in range(3):
        book = create_book(
            client,
            librarian_token,
            isbn=f"978000000{i}000"[:13],
            title=f"Book {i}",
        )
        response = client.post(
            "/loans/",
            json={"book_id": book["id"], "reader_id": reader_id},
            headers=auth_headers(librarian_token),
        )
        assert response.status_code == 201, response.text

    fourth_book = create_book(client, librarian_token, isbn="9789999999999", title="Book 4")
    response = client.post(
        "/loans/",
        json={"book_id": fourth_book["id"], "reader_id": reader_id},
        headers=auth_headers(librarian_token),
    )
    assert response.status_code == 400
    assert "active loans" in response.json()["detail"].lower()


def test_return_loan_without_delay_has_no_fine(client, librarian_token, reader_token_and_id):
    _, reader_id = reader_token_and_id
    book = create_book(client, librarian_token)

    loan = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader_id},
        headers=auth_headers(librarian_token),
    ).json()

    response = client.post(f"/loans/{loan['id']}/return", headers=auth_headers(librarian_token))
    assert response.status_code == 200
    body = response.json()
    assert body["return_date"] == date.today().isoformat()
    assert body["fine_amount"] == 0.0

    book_after = client.get(f"/books/{book['id']}", headers=auth_headers(librarian_token)).json()
    assert book_after["available_quantity"] == book["total_quantity"]


def test_return_loan_with_delay_calculates_fine(client, librarian_token, reader_token_and_id):
    _, reader_id = reader_token_and_id
    book = create_book(client, librarian_token)

    loan = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader_id},
        headers=auth_headers(librarian_token),
    ).json()

    # Backdate the due_date directly in the DB to simulate an overdue loan.
    session = client.SessionLocal()
    db_loan = session.get(Loan, loan["id"])
    db_loan.due_date = date.today() - timedelta(days=5)
    session.commit()
    session.close()

    response = client.post(f"/loans/{loan['id']}/return", headers=auth_headers(librarian_token))
    assert response.status_code == 200
    body = response.json()
    assert body["fine_amount"] == 5.0  # 5 days late * FINE_PER_DAY (1.00)


def test_cannot_return_already_returned_loan(client, librarian_token, reader_token_and_id):
    _, reader_id = reader_token_and_id
    book = create_book(client, librarian_token)

    loan = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader_id},
        headers=auth_headers(librarian_token),
    ).json()

    first = client.post(f"/loans/{loan['id']}/return", headers=auth_headers(librarian_token))
    assert first.status_code == 200

    second = client.post(f"/loans/{loan['id']}/return", headers=auth_headers(librarian_token))
    assert second.status_code == 400


def test_reader_can_list_own_active_loans(client, librarian_token, reader_token_and_id):
    reader_token, reader_id = reader_token_and_id
    book = create_book(client, librarian_token)

    client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader_id},
        headers=auth_headers(librarian_token),
    )

    response = client.get("/loans/me?active_only=true", headers=auth_headers(reader_token))
    assert response.status_code == 200
    loans = response.json()
    assert len(loans) == 1
    assert loans[0]["reader_id"] == reader_id


def test_reader_cannot_list_other_readers_loans(client, librarian_token, reader_token_and_id):
    reader_token, _ = reader_token_and_id
    other_reader = register_user(client, "reader3", "reader3@example.com", "senha123", "leitor")

    response = client.get(f"/loans/reader/{other_reader['id']}", headers=auth_headers(reader_token))
    assert response.status_code == 403


def test_librarian_can_list_any_reader_loans(client, librarian_token, reader_token_and_id):
    _, reader_id = reader_token_and_id
    book = create_book(client, librarian_token)

    client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader_id},
        headers=auth_headers(librarian_token),
    )

    response = client.get(f"/loans/reader/{reader_id}", headers=auth_headers(librarian_token))
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_loan_nonexistent_book_returns_404(client, librarian_token, reader_token_and_id):
    _, reader_id = reader_token_and_id
    response = client.post(
        "/loans/",
        json={"book_id": 9999, "reader_id": reader_id},
        headers=auth_headers(librarian_token),
    )
    assert response.status_code == 404


def test_loan_nonexistent_reader_returns_404(client, librarian_token):
    book = create_book(client, librarian_token)
    response = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": 9999},
        headers=auth_headers(librarian_token),
    )
    assert response.status_code == 404


def test_cannot_loan_to_a_librarian(client, librarian_token):
    book = create_book(client, librarian_token)
    librarian = register_user(client, "lib2", "lib2@example.com", "senha123", "bibliotecario")
    response = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": librarian["id"]},
        headers=auth_headers(librarian_token),
    )
    assert response.status_code == 400
