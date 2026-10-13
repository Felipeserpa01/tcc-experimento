import pytest

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models import UserRole
from app.schemas.user import UserCreate
from app.services import user_service
from tests.conftest import PASSWORD


def test_create_user_stores_hashed_password(db_session):
    user = user_service.create_user(db_session, UserCreate(name="Ana", email="ana@example.com", password="abc12345"))

    assert user.id is not None
    assert user.role == UserRole.READER
    assert user.hashed_password != "abc12345"


def test_duplicate_email_is_rejected(db_session, reader):
    with pytest.raises(ConflictError):
        user_service.create_user(db_session, UserCreate(name="Outro", email=reader.email.upper(), password="abc12345"))


def test_authenticate(db_session, reader):
    assert user_service.authenticate(db_session, reader.email, PASSWORD).id == reader.id
    assert user_service.authenticate(db_session, reader.email, "senhaErrada1") is None
    assert user_service.authenticate(db_session, "naoexiste@example.com", PASSWORD) is None


def test_get_unknown_user_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        user_service.get_user(db_session, 999)


class TestEnsureFirstLibrarian:
    def test_creates_configured_librarian_only_once(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "first_librarian_email", "admin@example.com")
        monkeypatch.setattr(settings, "first_librarian_password", "admin12345")

        user_service.ensure_first_librarian(db_session)
        user_service.ensure_first_librarian(db_session)

        librarians, total = user_service.list_users(db_session, UserRole.LIBRARIAN, skip=0, limit=10)
        assert total == 1
        assert librarians[0].email == "admin@example.com"
        assert user_service.authenticate(db_session, "admin@example.com", "admin12345") is not None

    def test_does_nothing_when_not_configured(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "first_librarian_email", None)
        monkeypatch.setattr(settings, "first_librarian_password", None)

        user_service.ensure_first_librarian(db_session)

        assert user_service.list_users(db_session, None, skip=0, limit=10)[1] == 0
