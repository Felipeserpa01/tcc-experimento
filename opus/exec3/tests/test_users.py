from app.models.user import UserRole
from tests.utils import auth_headers

NEW_LIBRARIAN = {"name": "Carlos", "email": "carlos@example.com", "password": "senhaForte123", "role": "librarian"}


def test_librarian_can_create_another_librarian(client, librarian_headers) -> None:
    response = client.post("/users", json=NEW_LIBRARIAN, headers=librarian_headers)

    assert response.status_code == 201
    assert response.json()["role"] == "librarian"


def test_reader_cannot_create_users(client, reader_headers) -> None:
    response = client.post("/users", json=NEW_LIBRARIAN, headers=reader_headers)
    assert response.status_code == 403


def test_librarian_lists_users_filtered_by_role(client, librarian_headers, make_user) -> None:
    make_user(role=UserRole.READER)
    make_user(role=UserRole.READER)

    response = client.get("/users", params={"role": "reader"}, headers=librarian_headers)

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert {user["role"] for user in response.json()} == {"reader"}


def test_reader_cannot_list_users(client, reader_headers) -> None:
    assert client.get("/users", headers=reader_headers).status_code == 403


def test_reader_can_read_own_profile_but_not_others(client, reader, reader_headers, make_user) -> None:
    other = make_user()

    assert client.get(f"/users/{reader.id}", headers=reader_headers).status_code == 200
    assert client.get(f"/users/{other.id}", headers=reader_headers).status_code == 403


def test_read_unknown_user_returns_404(client, librarian_headers) -> None:
    response = client.get("/users/99999", headers=librarian_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Usuário não encontrado."}


def test_role_is_read_from_database_not_from_token(client, db, reader) -> None:
    headers = auth_headers(reader)  # token emitido enquanto era leitor
    reader.role = UserRole.LIBRARIAN
    db.commit()

    assert client.get("/users", headers=headers).status_code == 200
