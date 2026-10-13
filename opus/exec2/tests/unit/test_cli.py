from app.cli import main
from app.models import UserRole
from app.services.user_service import get_user_by_email


def test_create_librarian_command(session_factory, db_session, capsys):
    exit_code = main(
        ["create-librarian", "--name", "Maria Lima", "--email", "maria@example.com", "--password", "Senha123"],
        session_factory=session_factory,
    )

    assert exit_code == 0
    assert "Bibliotecário criado" in capsys.readouterr().out
    assert get_user_by_email(db_session, "maria@example.com").role == UserRole.LIBRARIAN


def test_create_librarian_command_reports_errors(session_factory, capsys):
    args = ["create-librarian", "--name", "Maria", "--email", "maria@example.com"]

    assert main([*args, "--password", "fraca"], session_factory=session_factory) == 1
    assert "password" in capsys.readouterr().err

    assert main([*args, "--password", "Senha123"], session_factory=session_factory) == 0
    assert main([*args, "--password", "Senha123"], session_factory=session_factory) == 1
    assert "e-mail" in capsys.readouterr().err
