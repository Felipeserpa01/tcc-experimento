"""Comandos administrativos.

Uso:
    python -m app.cli create-librarian --name "Maria Lima" --email maria@biblioteca.com

Se `--password` for omitido, a senha é solicitada sem eco no terminal.
"""

import argparse
import getpass
import sys
from collections.abc import Sequence

from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import AppError
from app.db.session import SessionLocal, init_db
from app.models import User, UserRole
from app.schemas.user import UserCreate
from app.services import user_service


def create_librarian(session_factory: sessionmaker[Session], name: str, email: str, password: str) -> User:
    data = UserCreate(name=name, email=email, password=password, role=UserRole.LIBRARIAN)
    with session_factory() as db:
        return user_service.create_user(db, data)


def main(argv: Sequence[str] | None = None, session_factory: sessionmaker[Session] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Comandos administrativos da biblioteca")
    subcommands = parser.add_subparsers(dest="command", required=True)

    create = subcommands.add_parser("create-librarian", help="Cria um usuário bibliotecário")
    create.add_argument("--name", required=True)
    create.add_argument("--email", required=True)
    create.add_argument("--password", help="Senha (se omitida, será solicitada interativamente)")

    args = parser.parse_args(argv)

    if session_factory is None:
        init_db()
        session_factory = SessionLocal

    password = args.password or getpass.getpass("Senha: ")
    try:
        user = create_librarian(session_factory, args.name, args.email, password)
    except ValidationError as exc:
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"])
            print(f"Erro em '{field}': {error['msg']}", file=sys.stderr)
        return 1
    except AppError as exc:
        print(f"Erro: {exc.detail}", file=sys.stderr)
        return 1

    print(f"Bibliotecário criado: id={user.id}, e-mail={user.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
