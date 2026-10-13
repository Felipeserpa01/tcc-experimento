import pytest

from tests.conftest import PASSWORD, auth_headers


@pytest.fixture
def lend(client, librarian_headers):
    def _lend(book, reader, **extra):
        return client.post(
            "/loans", json={"book_id": book.id, "reader_id": reader.id, **extra}, headers=librarian_headers
        )

    return _lend


@pytest.fixture
def give_back(client, librarian_headers):
    def _give_back(loan_id: int):
        return client.post(f"/loans/{loan_id}/return", headers=librarian_headers)

    return _give_back


class TestCreateLoan:
    def test_librarian_registers_loan(self, client, lend, book_factory, reader, librarian_headers, clock):
        book = book_factory(total_quantity=2)

        response = lend(book, reader)

        assert response.status_code == 201
        loan = response.json()
        assert loan["status"] == "active"
        assert loan["loan_date"] == "2026-03-02"
        assert loan["due_date"] == "2026-03-16"  # prazo padrão de 14 dias
        assert loan["return_date"] is None
        assert loan["fine_amount"] == "0.00"
        assert loan["book"]["title"] == book.title
        assert loan["reader"]["id"] == reader.id

        book_after = client.get(f"/books/{book.id}", headers=librarian_headers).json()
        assert book_after["available_quantity"] == 1

    def test_custom_due_date(self, lend, book_factory, reader):
        response = lend(book_factory(), reader, due_date="2026-03-09")
        assert response.status_code == 201
        assert response.json()["due_date"] == "2026-03-09"

    def test_due_date_in_the_past_returns_422(self, lend, book_factory, reader):
        response = lend(book_factory(), reader, due_date="2026-03-01")
        assert response.status_code == 422
        assert response.json()["code"] == "invalid_due_date"

    def test_book_without_available_copies_returns_409(self, lend, book_factory, reader, other_reader):
        book = book_factory(total_quantity=1)
        assert lend(book, reader).status_code == 201

        response = lend(book, other_reader)

        assert response.status_code == 409
        assert response.json()["code"] == "book_unavailable"

    def test_reader_limited_to_three_simultaneous_loans(self, lend, give_back, book_factory, reader):
        loans = [lend(book_factory(), reader) for _ in range(3)]
        assert all(r.status_code == 201 for r in loans)

        fourth_book = book_factory()
        response = lend(fourth_book, reader)
        assert response.status_code == 409
        assert response.json()["code"] == "loan_limit_reached"

        # Após devolver um livro, o leitor volta a poder pegar emprestado.
        give_back(loans[0].json()["id"])
        assert lend(fourth_book, reader).status_code == 201

    def test_loan_to_librarian_returns_422(self, lend, book_factory, librarian):
        response = lend(book_factory(), librarian)
        assert response.status_code == 422
        assert response.json()["code"] == "not_a_reader"

    def test_unknown_book_returns_404(self, client, librarian_headers, reader):
        response = client.post("/loans", json={"book_id": 999, "reader_id": reader.id}, headers=librarian_headers)
        assert response.status_code == 404
        assert response.json()["code"] == "book_not_found"

    def test_unknown_reader_returns_404(self, client, librarian_headers, book_factory):
        response = client.post(
            "/loans", json={"book_id": book_factory().id, "reader_id": 999}, headers=librarian_headers
        )
        assert response.status_code == 404
        assert response.json()["code"] == "user_not_found"

    def test_invalid_payload_returns_422(self, client, librarian_headers):
        response = client.post("/loans", json={"book_id": "abc", "due_date": "ontem"}, headers=librarian_headers)
        assert response.status_code == 422

    def test_reader_cannot_register_loan(self, client, reader_headers, book_factory, reader):
        response = client.post(
            "/loans", json={"book_id": book_factory().id, "reader_id": reader.id}, headers=reader_headers
        )
        assert response.status_code == 403


class TestReturnLoan:
    def test_return_on_time_has_no_fine(self, client, lend, give_back, book_factory, reader, librarian_headers, clock):
        book = book_factory(total_quantity=1)
        loan_id = lend(book, reader).json()["id"]
        clock.advance(14)  # exatamente na data prevista

        response = give_back(loan_id)

        assert response.status_code == 200
        loan = response.json()
        assert loan["status"] == "returned"
        assert loan["return_date"] == "2026-03-16"
        assert loan["days_overdue"] == 0
        assert loan["fine_amount"] == "0.00"
        assert client.get(f"/books/{book.id}", headers=librarian_headers).json()["available_quantity"] == 1

    def test_late_return_calculates_fine(self, lend, give_back, book_factory, reader, clock):
        loan_id = lend(book_factory(), reader).json()["id"]
        clock.advance(14 + 6)  # 6 dias após a data prevista

        loan = give_back(loan_id).json()

        assert loan["return_date"] == "2026-03-22"
        assert loan["days_overdue"] == 6
        assert loan["fine_amount"] == "12.00"  # 6 dias x R$ 2,00

    def test_returning_twice_returns_409(self, lend, give_back, book_factory, reader):
        loan_id = lend(book_factory(), reader).json()["id"]
        give_back(loan_id)

        response = give_back(loan_id)

        assert response.status_code == 409
        assert response.json()["code"] == "loan_already_returned"

    def test_unknown_loan_returns_404(self, give_back):
        assert give_back(999).status_code == 404

    def test_reader_cannot_register_return(self, client, lend, book_factory, reader, reader_headers):
        loan_id = lend(book_factory(), reader).json()["id"]
        assert client.post(f"/loans/{loan_id}/return", headers=reader_headers).status_code == 403


class TestFine:
    def test_fine_accumulates_while_loan_is_active(self, client, lend, book_factory, reader, reader_headers, clock):
        loan_id = lend(book_factory(), reader).json()["id"]

        on_time = client.get(f"/loans/{loan_id}/fine", headers=reader_headers).json()
        assert on_time["amount"] == "0.00"

        clock.advance(14 + 3)
        late = client.get(f"/loans/{loan_id}/fine", headers=reader_headers).json()
        assert late == {
            "loan_id": loan_id,
            "due_date": "2026-03-16",
            "reference_date": "2026-03-19",
            "days_overdue": 3,
            "daily_fine": "2.00",
            "amount": "6.00",
            "is_final": False,
        }

    def test_fine_is_frozen_after_return(self, client, lend, give_back, book_factory, reader, reader_headers, clock):
        loan_id = lend(book_factory(), reader).json()["id"]
        clock.advance(14 + 2)
        give_back(loan_id)
        clock.advance(30)

        fine = client.get(f"/loans/{loan_id}/fine", headers=reader_headers).json()

        assert fine["amount"] == "4.00"
        assert fine["days_overdue"] == 2
        assert fine["is_final"] is True

    def test_other_reader_cannot_see_fine(self, client, lend, book_factory, reader, other_reader):
        loan_id = lend(book_factory(), reader).json()["id"]
        response = client.get(f"/loans/{loan_id}/fine", headers=auth_headers(other_reader))
        assert response.status_code == 403


class TestListLoans:
    def test_active_loans_of_reader(
        self, client, lend, give_back, book_factory, reader, other_reader, librarian_headers
    ):
        first = lend(book_factory(), reader).json()
        returned = lend(book_factory(), reader).json()
        give_back(returned["id"])
        lend(book_factory(), other_reader)

        response = client.get(f"/users/{reader.id}/loans/active", headers=librarian_headers)

        assert response.status_code == 200
        assert [loan["id"] for loan in response.json()] == [first["id"]]

    def test_reader_sees_own_active_loans_but_not_others(self, client, lend, book_factory, reader, other_reader):
        lend(book_factory(), reader)
        headers = auth_headers(reader)

        assert len(client.get(f"/users/{reader.id}/loans/active", headers=headers).json()) == 1
        assert client.get(f"/users/{other_reader.id}/loans/active", headers=headers).status_code == 403

    def test_active_loans_of_unknown_user_returns_404(self, client, librarian_headers):
        assert client.get("/users/999/loans/active", headers=librarian_headers).status_code == 404

    def test_librarian_lists_all_loans_with_filters(
        self, client, lend, give_back, book_factory, reader, other_reader, librarian_headers
    ):
        lend(book_factory(), reader)
        returned = lend(book_factory(), reader).json()
        give_back(returned["id"])
        lend(book_factory(), other_reader)

        all_loans = client.get("/loans", headers=librarian_headers).json()
        returned_loans = client.get("/loans", params={"status": "returned"}, headers=librarian_headers).json()
        reader_active = client.get(
            "/loans", params={"reader_id": reader.id, "status": "active"}, headers=librarian_headers
        ).json()

        assert all_loans["total"] == 3
        assert [loan["id"] for loan in returned_loans["items"]] == [returned["id"]]
        assert reader_active["total"] == 1

    def test_reader_only_sees_own_loans(self, client, lend, book_factory, reader, other_reader):
        lend(book_factory(), reader)
        lend(book_factory(), other_reader)
        headers = auth_headers(reader)

        body = client.get("/loans", headers=headers).json()
        assert body["total"] == 1
        assert body["items"][0]["reader_id"] == reader.id

        assert client.get("/loans", params={"reader_id": other_reader.id}, headers=headers).status_code == 403

    def test_overdue_filter(self, client, lend, book_factory, reader, librarian_headers, clock):
        late = lend(book_factory(), reader, due_date="2026-03-05").json()
        lend(book_factory(), reader, due_date="2026-03-30")
        clock.advance(10)

        body = client.get("/loans", params={"overdue": True}, headers=librarian_headers).json()

        assert body["total"] == 1
        assert body["items"][0]["id"] == late["id"]
        assert body["items"][0]["days_overdue"] == 7
        assert body["items"][0]["fine_amount"] == "14.00"

    def test_get_loan_permissions(self, client, lend, book_factory, reader, other_reader):
        loan_id = lend(book_factory(), reader).json()["id"]

        assert client.get(f"/loans/{loan_id}", headers=auth_headers(reader)).status_code == 200
        assert client.get(f"/loans/{loan_id}", headers=auth_headers(other_reader)).status_code == 403
        assert client.get("/loans/999", headers=auth_headers(reader)).status_code == 404


def test_full_library_flow(client, clock, librarian):
    """Fluxo completo pela API: cadastro, login, livro, empréstimo, atraso e devolução com multa."""

    def login(email: str, password: str) -> dict[str, str]:
        token = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    client.post("/auth/register", json={"name": "Leitor", "email": "leitor@example.com", "password": "leitor1234"})
    reader_headers = login("leitor@example.com", "leitor1234")
    reader_id = client.get("/users/me", headers=reader_headers).json()["id"]
    librarian_headers = login(librarian.email, PASSWORD)

    book = client.post(
        "/books",
        json={
            "title": "Vidas Secas",
            "author": "Graciliano Ramos",
            "isbn": "9780306406157",
            "year": 1938,
            "total_quantity": 1,
        },
        headers=librarian_headers,
    ).json()
    loan = client.post("/loans", json={"book_id": book["id"], "reader_id": reader_id}, headers=librarian_headers).json()
    assert client.get(f"/books/{book['id']}", headers=reader_headers).json()["available_quantity"] == 0
    assert len(client.get(f"/users/{reader_id}/loans/active", headers=reader_headers).json()) == 1

    clock.advance(14 + 10)
    returned = client.post(f"/loans/{loan['id']}/return", headers=librarian_headers).json()

    assert returned["days_overdue"] == 10
    assert returned["fine_amount"] == "20.00"
    assert client.get(f"/books/{book['id']}", headers=reader_headers).json()["available_quantity"] == 1
    assert client.get(f"/users/{reader_id}/loans/active", headers=reader_headers).json() == []
