def test_librarian_lists_users_filtered_by_role(client, librarian_headers, make_user):
    make_user()
    make_user()

    response = client.get("/users", params={"role": "reader"}, headers=librarian_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {user["role"] for user in body["items"]} == {"reader"}


def test_reader_cannot_list_users(client, reader_headers):
    assert client.get("/users", headers=reader_headers).status_code == 403


def test_reader_can_only_see_own_profile(client, reader, reader_headers, make_user):
    other = make_user()

    assert client.get(f"/users/{reader.id}", headers=reader_headers).status_code == 200
    assert client.get(f"/users/{other.id}", headers=reader_headers).status_code == 403


def test_get_unknown_user_returns_404(client, librarian_headers):
    response = client.get("/users/999", headers=librarian_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Usuário não encontrado", "code": "user_not_found"}
