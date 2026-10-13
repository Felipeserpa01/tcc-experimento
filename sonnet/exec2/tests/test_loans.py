from datetime import date, timedelta

from app.models import Loan


def create_book(client, headers, **overrides):
    payload = {
        "title": "Dom Casmurro",
        "author": "Machado de Assis",
        "isbn": "978-8535910663",
        "year": 1899,
        "total_copies": 1,
    }
    payload.update(overrides)
    return client.post("/books/", json=payload, headers=headers).json()


def test_librarian_can_register_loan(client, librarian, reader):
    book = create_book(client, librarian["headers"])
    response = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    assert response.status_code == 201
    loan = response.json()
    assert loan["book_id"] == book["id"]
    assert loan["reader_id"] == reader["user"]["id"]
    assert loan["return_date"] is None

    book_after = client.get(f"/books/{book['id']}", headers=librarian["headers"]).json()
    assert book_after["available_copies"] == 0


def test_reader_cannot_register_loan(client, librarian, reader):
    book = create_book(client, librarian["headers"])
    response = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader["user"]["id"]},
        headers=reader["headers"],
    )
    assert response.status_code == 403


def test_cannot_loan_book_without_available_copies(client, librarian, make_reader):
    book = create_book(client, librarian["headers"], total_copies=1)
    reader1 = make_reader()
    reader2 = make_reader()

    first = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader1["user"]["id"]},
        headers=librarian["headers"],
    )
    assert first.status_code == 201

    second = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader2["user"]["id"]},
        headers=librarian["headers"],
    )
    assert second.status_code == 400
    assert "available" in second.json()["detail"].lower()


def test_reader_cannot_exceed_max_simultaneous_loans(client, librarian, reader):
    for i in range(3):
        book = create_book(
            client, librarian["headers"], title=f"Book {i}", isbn=f"978-000000000{i}"
        )
        response = client.post(
            "/loans/",
            json={"book_id": book["id"], "reader_id": reader["user"]["id"]},
            headers=librarian["headers"],
        )
        assert response.status_code == 201

    extra_book = create_book(client, librarian["headers"], title="Book 3", isbn="978-0000000099")
    response = client.post(
        "/loans/",
        json={"book_id": extra_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    assert response.status_code == 400
    assert "maximum" in response.json()["detail"].lower()


def test_return_loan_on_time_has_no_fine(client, librarian, reader):
    book = create_book(client, librarian["headers"])
    loan = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    ).json()

    response = client.put(f"/loans/{loan['id']}/return", headers=librarian["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["fine"] == 0.0
    assert data["days_late"] == 0
    assert data["return_date"] is not None

    book_after = client.get(f"/books/{book['id']}", headers=librarian["headers"]).json()
    assert book_after["available_copies"] == 1


def test_return_late_loan_calculates_fine(client, librarian, reader, db_session):
    book = create_book(client, librarian["headers"])
    loan = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    ).json()

    db_loan = db_session.get(Loan, loan["id"])
    db_loan.due_date = date.today() - timedelta(days=5)
    db_session.commit()

    response = client.put(f"/loans/{loan['id']}/return", headers=librarian["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["days_late"] == 5
    assert data["fine"] == 5.0


def test_cannot_return_already_returned_loan(client, librarian, reader):
    book = create_book(client, librarian["headers"])
    loan = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    ).json()
    client.put(f"/loans/{loan['id']}/return", headers=librarian["headers"])

    response = client.put(f"/loans/{loan['id']}/return", headers=librarian["headers"])
    assert response.status_code == 400


def test_list_active_loans_of_reader(client, librarian, reader):
    book1 = create_book(client, librarian["headers"], title="Book A", isbn="978-1111111111")
    book2 = create_book(client, librarian["headers"], title="Book B", isbn="978-2222222222")

    loan1 = client.post(
        "/loans/",
        json={"book_id": book1["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    ).json()
    client.post(
        "/loans/",
        json={"book_id": book2["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    client.put(f"/loans/{loan1['id']}/return", headers=librarian["headers"])

    response = client.get(
        f"/loans/reader/{reader['user']['id']}/active", headers=librarian["headers"]
    )
    assert response.status_code == 200
    active_loans = response.json()
    assert len(active_loans) == 1
    assert active_loans[0]["book_id"] == book2["id"]


def test_reader_can_view_own_active_loans(client, librarian, reader):
    book = create_book(client, librarian["headers"])
    client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )

    response = client.get(
        f"/loans/reader/{reader['user']['id']}/active", headers=reader["headers"]
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_reader_cannot_view_other_readers_active_loans(client, librarian, make_reader):
    reader1 = make_reader()
    reader2 = make_reader()
    book = create_book(client, librarian["headers"])
    client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": reader1["user"]["id"]},
        headers=librarian["headers"],
    )

    response = client.get(
        f"/loans/reader/{reader1['user']['id']}/active", headers=reader2["headers"]
    )
    assert response.status_code == 403


def test_loan_nonexistent_book_returns_404(client, librarian, reader):
    response = client.post(
        "/loans/",
        json={"book_id": 999, "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    assert response.status_code == 404


def test_loan_nonexistent_reader_returns_404(client, librarian):
    book = create_book(client, librarian["headers"])
    response = client.post(
        "/loans/",
        json={"book_id": book["id"], "reader_id": 999},
        headers=librarian["headers"],
    )
    assert response.status_code == 404
