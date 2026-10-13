"""Utilitários de linha de comando.

Uso::

    python -m app.cli init-db
    python -m app.cli create-admin --email admin@clinica.com.br --name "Ana Administradora"

A senha do administrador é solicitada de forma interativa (nunca via argumento).
"""

import argparse
import getpass
import sys

from pydantic import TypeAdapter, ValidationError

from app.core.database import get_session_factory, init_db
from app.core.exceptions import AppError
from app.schemas.common import Email, PersonName
from app.services.user_service import UserService


def _create_admin(email: str, name: str) -> int:
    try:
        email = TypeAdapter(Email).validate_python(email)
        name = TypeAdapter(PersonName).validate_python(name)
    except ValidationError as exc:
        print(f"Dados inválidos: {exc.errors()[0]['msg']}", file=sys.stderr)
        return 1

    password = getpass.getpass("Senha: ")
    if password != getpass.getpass("Confirme a senha: "):
        print("As senhas não conferem.", file=sys.stderr)
        return 1

    init_db()
    with get_session_factory()() as session:
        try:
            admin = UserService(session).create_admin(email, name, password, origin="linha_de_comando")
        except (AppError, ValueError) as exc:
            print(f"Erro: {getattr(exc, 'message', exc)}", file=sys.stderr)
            return 1
    print(f"Administrador criado com sucesso (id={admin.id}).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Ferramentas administrativas da API")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="Cria as tabelas do banco de dados")
    admin = commands.add_parser("create-admin", help="Cria um usuário administrador")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)

    args = parser.parse_args(argv)
    if args.command == "init-db":
        init_db()
        print("Banco de dados inicializado.")
        return 0
    return _create_admin(args.email, args.name)


if __name__ == "__main__":
    sys.exit(main())
