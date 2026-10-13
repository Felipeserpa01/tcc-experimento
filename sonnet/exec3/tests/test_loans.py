from datetime import datetime, timedelta

from app import models
from app.database import SessionLocal


def test_create_loan_success(client, librarian, reader, sample_book):
    resp = client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["book_id"] == sample_book["id"]
    assert data["reader_id"] == reader["user"]["id"]
    assert data["return_date"] is None
    assert data["fine_amount"] == 0.0

    book_resp = client.get(f"/books/{sample_book['id']}", headers=librarian["headers"])
    assert book_resp.json()["available_quantity"] == sample_book["available_quantity"] - 1


def test_create_loan_as_reader_forbidden(client, reader, sample_book):
    resp = client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=reader["headers"],
    )
    assert resp.status_code == 403


def test_create_loan_nonexistent_book(client, librarian, reader):
    resp = client.post(
        "/loans/",
        json={"book_id": 9999, "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    assert resp.status_code == 404


def test_create_loan_nonexistent_reader(client, librarian, sample_book):
    resp = client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": 9999},
        headers=librarian["headers"],
    )
    assert resp.status_code == 404


def test_create_loan_no_copies_available(client, librarian, make_reader, sample_book):
    reader_a = make_reader()
    reader_b = make_reader()
    reader_c = make_reader()

    for r in (reader_a, reader_b):
        resp = client.post(
            "/loans/",
            json={"book_id": sample_book["id"], "reader_id": r["user"]["id"]},
            headers=librarian["headers"],
        )
        assert resp.status_code == 201

    resp = client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader_c["user"]["id"]},
        headers=librarian["headers"],
    )
    assert resp.status_code == 400


def test_reader_max_active_loans_limit(client, librarian, reader):
    book_ids = []
    for i in range(4):
        resp = client.post(
            "/books/",
            json={
                "title": f"Livro {i}",
                "author": "Autor",
                "isbn": f"999000000000{i}",
                "year": 2000 + i,
                "total_quantity": 1,
            },
            headers=librarian["headers"],
        )
        assert resp.status_code == 201
        book_ids.append(resp.json()["id"])

    for book_id in book_ids[:3]:
        resp = client.post(
            "/loans/",
            json={"book_id": book_id, "reader_id": reader["user"]["id"]},
            headers=librarian["headers"],
        )
        assert resp.status_code == 201

    resp = client.post(
        "/loans/",
        json={"book_id": book_ids[3], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    assert resp.status_code == 400


def test_return_loan_on_time_no_fine(client, librarian, reader, sample_book):
    loan_resp = client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    loan_id = loan_resp.json()["id"]

    resp = client.post(f"/loans/{loan_id}/return", headers=librarian["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["return_date"] is not None
    assert data["fine_amount"] == 0.0

    book_resp = client.get(f"/books/{sample_book['id']}", headers=librarian["headers"])
    assert book_resp.json()["available_quantity"] == sample_book["available_quantity"]


def test_return_loan_already_returned_fails(client, librarian, reader, sample_book):
    loan_resp = client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    loan_id = loan_resp.json()["id"]

    client.post(f"/loans/{loan_id}/return", headers=librarian["headers"])
    resp = client.post(f"/loans/{loan_id}/return", headers=librarian["headers"])
    assert resp.status_code == 400


def test_return_loan_not_found(client, librarian):
    resp = client.post("/loans/9999/return", headers=librarian["headers"])
    assert resp.status_code == 404


def test_return_loan_late_calculates_fine(client, librarian, reader, sample_book):
    loan_resp = client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    loan_id = loan_resp.json()["id"]

    db = SessionLocal()
    try:
        loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
        loan.due_date = datetime.utcnow() - timedelta(days=5)
        db.commit()
    finally:
        db.close()

    resp = client.post(f"/loans/{loan_id}/return", headers=librarian["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["fine_amount"] == 5.0


def test_list_my_active_loans(client, librarian, reader, sample_book):
    client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    resp = client.get("/loans/me", headers=reader["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["reader_id"] == reader["user"]["id"]


def test_list_reader_loans_as_librarian(client, librarian, reader, sample_book):
    client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    resp = client.get(
        f"/loans/reader/{reader['user']['id']}", headers=librarian["headers"]
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_reader_loans_other_reader_forbidden(client, librarian, reader, make_reader, sample_book):
    other_reader = make_reader()
    client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    resp = client.get(
        f"/loans/reader/{reader['user']['id']}", headers=other_reader["headers"]
    )
    assert resp.status_code == 403


def test_list_all_loans_as_librarian(client, librarian, reader, sample_book):
    client.post(
        "/loans/",
        json={"book_id": sample_book["id"], "reader_id": reader["user"]["id"]},
        headers=librarian["headers"],
    )
    resp = client.get("/loans/", headers=librarian["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_all_loans_as_reader_forbidden(client, reader):
    resp = client.get("/loans/", headers=reader["headers"])
    assert resp.status_code == 403
