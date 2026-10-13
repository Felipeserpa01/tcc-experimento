import pytest

from app.core.config import settings


@pytest.fixture
def lend(client, librarian_headers):
    def _lend(book, reader, **extra):
        return client.post(
            "/loans", json={"book_id": book.id, "reader_id": reader.id, **extra}, headers=librarian_headers
        )

    return _lend


def test_register_loan(client, lend, librarian_headers, make_book, reader):
    book = make_book(total_quantity=2)

    response = lend(book, reader)

    assert response.status_code == 201
    loan = response.json()
    assert loan["book"]["id"] == book.id
    assert loan["reader"]["id"] == reader.id
    assert loan["loan_date"].startswith("2026-03-02")
    assert loan["due_date"] == "2026-03-16"  # 14 dias por padrão
    assert loan["status"] == "active"
    assert loan["returned_at"] is None
    assert loan["fine_amount"] == 0
    assert client.get(f"/books/{book.id}", headers=librarian_headers).json()["available_quantity"] == 1


def test_loan_without_available_copies_returns_409(lend, make_book, make_user):
    book = make_book(total_quantity=1)
    assert lend(book, make_user()).status_code == 201

    response = lend(book, make_user())

    assert response.status_code == 409
    assert response.json()["code"] == "book_unavailable"


def test_reader_limited_to_three_active_loans(client, lend, librarian_headers, make_book, reader):
    loans = [lend(make_book(), reader) for _ in range(3)]
    assert all(response.status_code == 201 for response in loans)

    fourth = lend(make_book(), reader)
    assert fourth.status_code == 409
    assert fourth.json()["code"] == "loan_limit_reached"

    # Depois de devolver um livro, o leitor pode pegar outro.
    client.post(f"/loans/{loans[0].json()['id']}/return", headers=librarian_headers)
    assert lend(make_book(), reader).status_code == 201


def test_loan_to_librarian_returns_400(lend, make_book, librarian):
    response = lend(make_book(), librarian)

    assert response.status_code == 400
    assert response.json()["code"] == "user_not_reader"


def test_loan_with_unknown_book_or_reader_returns_404(client, librarian_headers, make_book, reader):
    unknown_book = client.post("/loans", json={"book_id": 999, "reader_id": reader.id}, headers=librarian_headers)
    unknown_reader = client.post("/loans", json={"book_id": make_book().id, "reader_id": 999}, headers=librarian_headers)

    assert unknown_book.status_code == 404
    assert unknown_reader.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [{}, {"book_id": 1}, {"book_id": "1", "reader_id": 2}, {"book_id": 1, "reader_id": 2, "loan_days": 0}],
)
def test_invalid_loan_payload_returns_422(client, librarian_headers, payload):
    assert client.post("/loans", json=payload, headers=librarian_headers).status_code == 422


def test_reader_cannot_register_loans_or_returns(client, reader_headers, make_book, reader, lend):
    loan = lend(make_book(), reader).json()

    assert client.post("/loans", json={"book_id": 1, "reader_id": reader.id}, headers=reader_headers).status_code == 403
    assert client.post(f"/loans/{loan['id']}/return", headers=reader_headers).status_code == 403


def test_on_time_return_has_no_fine(client, clock, lend, librarian_headers, make_book, reader):
    book = make_book()
    loan = lend(book, reader).json()
    clock.advance(days=14)  # exatamente na data prevista

    response = client.post(f"/loans/{loan['id']}/return", headers=librarian_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "returned"
    assert body["returned_at"].startswith("2026-03-16")
    assert body["days_overdue"] == 0
    assert body["fine_amount"] == 0
    assert client.get(f"/books/{book.id}", headers=librarian_headers).json()["available_quantity"] == 1


def test_late_return_calculates_fine(client, clock, lend, librarian_headers, make_book, reader):
    loan = lend(make_book(), reader, loan_days=7).json()  # vence em 09/03
    clock.advance(days=12)  # devolvido em 14/03: 5 dias de atraso

    body = client.post(f"/loans/{loan['id']}/return", headers=librarian_headers).json()

    assert body["days_overdue"] == 5
    assert body["fine_amount"] == float(settings.daily_fine * 5)

    # A multa fica registrada: consultar depois não altera o valor.
    clock.advance(days=30)
    assert client.get(f"/loans/{loan['id']}", headers=librarian_headers).json()["fine_amount"] == body["fine_amount"]


def test_return_twice_returns_409(client, lend, librarian_headers, make_book, reader):
    loan = lend(make_book(), reader).json()
    client.post(f"/loans/{loan['id']}/return", headers=librarian_headers)

    response = client.post(f"/loans/{loan['id']}/return", headers=librarian_headers)

    assert response.status_code == 409
    assert response.json()["code"] == "loan_already_returned"


def test_return_unknown_loan_returns_404(client, librarian_headers):
    assert client.post("/loans/999/return", headers=librarian_headers).status_code == 404


def test_list_active_loans_of_reader(client, clock, lend, librarian_headers, reader_headers, make_book, reader):
    on_time = lend(make_book(title="No prazo"), reader, loan_days=30).json()
    late = lend(make_book(title="Atrasado"), reader, loan_days=2).json()
    returned = lend(make_book(title="Devolvido"), reader).json()
    client.post(f"/loans/{returned['id']}/return", headers=librarian_headers)
    clock.advance(days=5)

    by_librarian = client.get(f"/users/{reader.id}/loans/active", headers=librarian_headers)
    by_reader = client.get("/users/me/loans/active", headers=reader_headers)

    assert by_librarian.status_code == by_reader.status_code == 200
    assert by_librarian.json() == by_reader.json()
    loans = {loan["id"]: loan for loan in by_librarian.json()}
    assert set(loans) == {on_time["id"], late["id"]}
    assert loans[on_time["id"]]["status"] == "active"
    assert loans[late["id"]]["status"] == "overdue"
    assert loans[late["id"]]["days_overdue"] == 3
    assert loans[late["id"]]["fine_amount"] == float(settings.daily_fine * 3)


def test_reader_cannot_see_other_readers_loans(client, lend, reader_headers, make_book, make_user):
    other = make_user()
    loan = lend(make_book(), other).json()

    assert client.get(f"/users/{other.id}/loans/active", headers=reader_headers).status_code == 403
    assert client.get(f"/loans/{loan['id']}", headers=reader_headers).status_code == 403
    assert client.get("/loans", params={"reader_id": other.id}, headers=reader_headers).status_code == 403


def test_active_loans_endpoint_rejects_non_readers(client, librarian, librarian_headers):
    assert client.get(f"/users/{librarian.id}/loans/active", headers=librarian_headers).status_code == 400
    assert client.get("/users/999/loans/active", headers=librarian_headers).status_code == 404


def test_reader_lists_only_own_loans(client, lend, reader_headers, make_book, make_user, reader):
    own = lend(make_book(), reader).json()
    lend(make_book(), make_user())

    body = client.get("/loans", headers=reader_headers).json()

    assert body["total"] == 1
    assert body["items"][0]["id"] == own["id"]


def test_librarian_filters_loans_by_status(client, clock, lend, librarian_headers, make_book, make_user):
    reader = make_user()
    lend(make_book(), reader, loan_days=30)
    late = lend(make_book(), reader, loan_days=1).json()
    returned = lend(make_book(), reader).json()
    client.post(f"/loans/{returned['id']}/return", headers=librarian_headers)
    clock.advance(days=3)

    def ids(status):
        body = client.get("/loans", params={"status": status}, headers=librarian_headers).json()
        return {loan["id"] for loan in body["items"]}

    assert len(ids("active")) == 2  # inclui o atrasado
    assert ids("overdue") == {late["id"]}
    assert ids("returned") == {returned["id"]}
    assert client.get("/loans", params={"status": "invalido"}, headers=librarian_headers).status_code == 422


def test_due_date_uses_library_local_date(client, clock, lend, make_book, reader):
    # 01h30 UTC de 03/03 ainda é 22h30 de 02/03 em São Paulo.
    clock.now = clock.now.replace(day=3, hour=1, minute=30)

    loan = lend(make_book(), reader).json()

    assert loan["due_date"] == "2026-03-16"
