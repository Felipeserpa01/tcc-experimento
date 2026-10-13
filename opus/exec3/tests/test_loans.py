import pytest

from app.models.user import UserRole
from tests.utils import auth_headers


def available(client, headers, book_id: int) -> int:
    return client.get(f"/books/{book_id}", headers=headers).json()["available_quantity"]


# ---------- Registro de empréstimo ----------


def test_create_loan(client, librarian_headers, make_book, reader, lend) -> None:
    book = make_book(total_quantity=2)

    response = lend(book["id"], reader.id)

    assert response.status_code == 201
    loan = response.json()
    assert loan["book"]["id"] == book["id"]
    assert loan["reader"]["id"] == reader.id
    assert loan["loan_date"] == "2026-03-02"
    assert loan["due_date"] == "2026-03-16"  # prazo padrão de 14 dias
    assert loan["return_date"] is None
    assert loan["status"] == "active"
    assert loan["days_overdue"] == 0
    assert loan["fine_amount"] == 0
    assert available(client, librarian_headers, book["id"]) == 1


def test_create_loan_with_custom_period(make_book, reader, lend) -> None:
    book = make_book()
    response = lend(book["id"], reader.id, loan_days=7)
    assert response.json()["due_date"] == "2026-03-09"


def test_cannot_lend_book_without_available_copies(client, librarian_headers, make_book, make_user, lend) -> None:
    book = make_book(total_quantity=1)
    assert lend(book["id"], make_user().id).status_code == 201

    response = lend(book["id"], make_user().id)

    assert response.status_code == 409
    assert "exemplares disponíveis" in response.json()["detail"]
    assert available(client, librarian_headers, book["id"]) == 0


def test_reader_limited_to_three_simultaneous_loans(client, librarian_headers, make_book, reader, lend) -> None:
    books = [make_book() for _ in range(4)]
    for book in books[:3]:
        assert lend(book["id"], reader.id).status_code == 201

    response = lend(books[3]["id"], reader.id)

    assert response.status_code == 409
    assert "limite de 3" in response.json()["detail"]
    # A tentativa recusada não pode consumir exemplar.
    assert available(client, librarian_headers, books[3]["id"]) == 2


def test_returning_a_book_frees_a_loan_slot(client, librarian_headers, make_book, reader, lend) -> None:
    books = [make_book() for _ in range(4)]
    loans = [lend(book["id"], reader.id).json() for book in books[:3]]

    client.post(f"/loans/{loans[0]['id']}/return", headers=librarian_headers)

    assert lend(books[3]["id"], reader.id).status_code == 201


def test_cannot_lend_to_librarian(make_book, librarian, lend) -> None:
    book = make_book()

    response = lend(book["id"], librarian.id)

    assert response.status_code == 422
    assert "leitor" in response.json()["detail"]


@pytest.mark.parametrize(
    ("use_valid_book", "use_valid_reader", "expected_detail"),
    [(False, True, "Livro não encontrado."), (True, False, "Leitor não encontrado.")],
)
def test_create_loan_with_unknown_book_or_reader(
    make_book, reader, lend, use_valid_book, use_valid_reader, expected_detail
) -> None:
    book = make_book()
    response = lend(book["id"] if use_valid_book else 99999, reader.id if use_valid_reader else 99999)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


@pytest.mark.parametrize(
    "payload",
    [{"book_id": 0, "reader_id": 1}, {"book_id": 1}, {"book_id": 1, "reader_id": 1, "loan_days": 0}],
)
def test_create_loan_validates_input(client, librarian_headers, payload: dict) -> None:
    assert client.post("/loans", json=payload, headers=librarian_headers).status_code == 422


def test_reader_cannot_register_loans(client, reader_headers, make_book, reader) -> None:
    book = make_book()
    response = client.post("/loans", json={"book_id": book["id"], "reader_id": reader.id}, headers=reader_headers)
    assert response.status_code == 403


# ---------- Devolução e multa ----------


def test_return_on_time_has_no_fine(client, librarian_headers, make_book, reader, lend, clock) -> None:
    book = make_book(total_quantity=1)
    loan = lend(book["id"], reader.id).json()
    clock.advance(14)  # exatamente na data prevista

    response = client.post(f"/loans/{loan['id']}/return", headers=librarian_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "returned"
    assert body["return_date"] == "2026-03-16"
    assert body["days_overdue"] == 0
    assert body["fine_amount"] == 0
    assert available(client, librarian_headers, book["id"]) == 1


def test_late_return_calculates_fine(client, librarian_headers, make_book, reader, lend, clock) -> None:
    loan = lend(make_book()["id"], reader.id).json()
    clock.advance(14 + 5)  # 5 dias após a data prevista

    body = client.post(f"/loans/{loan['id']}/return", headers=librarian_headers).json()

    assert body["return_date"] == "2026-03-21"
    assert body["days_overdue"] == 5
    assert body["fine_amount"] == 10.0  # 5 dias x R$ 2,00


def test_fine_is_frozen_after_return(client, librarian_headers, make_book, reader, lend, clock) -> None:
    loan = lend(make_book()["id"], reader.id).json()
    clock.advance(17)
    client.post(f"/loans/{loan['id']}/return", headers=librarian_headers)

    clock.advance(30)
    body = client.get(f"/loans/{loan['id']}", headers=librarian_headers).json()

    assert body["days_overdue"] == 3
    assert body["fine_amount"] == 6.0


def test_active_overdue_loan_shows_accumulated_fine(client, librarian_headers, make_book, reader, lend, clock) -> None:
    loan = lend(make_book()["id"], reader.id).json()
    clock.advance(16)

    body = client.get(f"/loans/{loan['id']}", headers=librarian_headers).json()

    assert body["status"] == "overdue"
    assert body["days_overdue"] == 2
    assert body["fine_amount"] == 4.0


def test_cannot_return_twice(client, librarian_headers, make_book, reader, lend) -> None:
    book = make_book(total_quantity=1)
    loan = lend(book["id"], reader.id).json()
    client.post(f"/loans/{loan['id']}/return", headers=librarian_headers)

    response = client.post(f"/loans/{loan['id']}/return", headers=librarian_headers)

    assert response.status_code == 409
    assert "já foi devolvido" in response.json()["detail"]
    assert available(client, librarian_headers, book["id"]) == 1  # não incrementou de novo


def test_return_unknown_loan(client, librarian_headers) -> None:
    assert client.post("/loans/99999/return", headers=librarian_headers).status_code == 404


def test_reader_cannot_register_return(client, reader_headers, make_book, reader, lend) -> None:
    loan = lend(make_book()["id"], reader.id).json()
    assert client.post(f"/loans/{loan['id']}/return", headers=reader_headers).status_code == 403


# ---------- Consultas ----------


@pytest.fixture
def reader_history(client, librarian_headers, make_book, reader, lend) -> dict:
    """Leitor com dois empréstimos ativos e um já devolvido."""
    active = [lend(make_book()["id"], reader.id).json() for _ in range(2)]
    returned = lend(make_book()["id"], reader.id).json()
    client.post(f"/loans/{returned['id']}/return", headers=librarian_headers)
    return {"active": active, "returned": returned}


def test_librarian_lists_active_loans_of_reader(client, librarian_headers, reader, reader_history) -> None:
    response = client.get(f"/users/{reader.id}/loans", headers=librarian_headers)

    assert response.status_code == 200
    assert {loan["id"] for loan in response.json()} == {loan["id"] for loan in reader_history["active"]}
    assert all(loan["status"] == "active" for loan in response.json())


def test_list_reader_loan_history(client, librarian_headers, reader, reader_history) -> None:
    response = client.get(f"/users/{reader.id}/loans", params={"active_only": False}, headers=librarian_headers)
    assert len(response.json()) == 3


def test_reader_lists_own_active_loans(client, reader_headers, reader_history) -> None:
    response = client.get("/users/me/loans", headers=reader_headers)

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_reader_cannot_see_loans_of_another_reader(client, make_user, reader, reader_history) -> None:
    other_headers = auth_headers(make_user(role=UserRole.READER))
    loan_id = reader_history["active"][0]["id"]

    assert client.get(f"/users/{reader.id}/loans", headers=other_headers).status_code == 403
    assert client.get(f"/loans/{loan_id}", headers=other_headers).status_code == 403


def test_reader_can_read_own_loan(client, reader_headers, reader_history) -> None:
    loan_id = reader_history["active"][0]["id"]
    assert client.get(f"/loans/{loan_id}", headers=reader_headers).status_code == 200


def test_list_loans_of_unknown_user(client, librarian_headers) -> None:
    assert client.get("/users/99999/loans", headers=librarian_headers).status_code == 404


def test_librarian_filters_overdue_loans(client, librarian_headers, make_book, make_user, lend, clock) -> None:
    late = lend(make_book()["id"], make_user().id, loan_days=3).json()
    lend(make_book()["id"], make_user().id, loan_days=30)
    clock.advance(10)

    response = client.get("/loans", params={"overdue_only": True}, headers=librarian_headers)

    assert [loan["id"] for loan in response.json()] == [late["id"]]
    assert len(client.get("/loans", headers=librarian_headers).json()) == 2


def test_librarian_filters_loans_by_reader_and_book(client, librarian_headers, make_book, make_user, lend) -> None:
    book, other_book = make_book(), make_book()
    reader, other_reader = make_user(), make_user()
    expected = lend(book["id"], reader.id).json()
    lend(other_book["id"], reader.id)
    lend(book["id"], other_reader.id)

    response = client.get(
        "/loans", params={"reader_id": reader.id, "book_id": book["id"]}, headers=librarian_headers
    )

    assert [loan["id"] for loan in response.json()] == [expected["id"]]


def test_reader_cannot_list_all_loans(client, reader_headers) -> None:
    assert client.get("/loans", headers=reader_headers).status_code == 403
