"""Comandos administrativos.

Uso:
    python -m app.cli create-librarian --name "Maria Silva" --email maria@biblioteca.com
"""

import argparse
import getpass
import sys

from pydantic import ValidationError

from app.core.exceptions import AppError
from app.db.session import SessionLocal, init_db
from app.models.user import UserRole
from app.schemas.user import UserCreate
from app.services import user_service


def create_librarian(name: str, email: str, password: str) -> int:
    try:
        data = UserCreate(name=name, email=email, password=password, role=UserRole.LIBRARIAN)
    except ValidationError as exc:
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"])
            print(f"Erro em '{field}': {error['msg']}", file=sys.stderr)
        return 1

    init_db()
    with SessionLocal() as db:
        try:
            user = user_service.create_user(db, data, role=data.role)
        except AppError as exc:
            print(f"Erro: {exc.detail}", file=sys.stderr)
            return 1

    print(f"Bibliotecário criado com sucesso (id={user.id}, e-mail={user.email}).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Comandos administrativos da biblioteca")
    subparsers = parser.add_subparsers(dest="command", required=True)

    librarian = subparsers.add_parser("create-librarian", help="Cria um usuário bibliotecário")
    librarian.add_argument("--name", required=True)
    librarian.add_argument("--email", required=True)
    librarian.add_argument("--password", help="Se omitida, será solicitada de forma interativa")

    args = parser.parse_args(argv)
    if args.command == "create-librarian":
        password = args.password or getpass.getpass("Senha: ")
        return create_librarian(args.name, args.email, password)
    return 1


if __name__ == "__main__":
    sys.exit(main())
