from app.core.security import create_access_token
from app.models.user import User


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


def make_isbn13(seed: int) -> str:
    """Gera um ISBN-13 válido (com dígito verificador correto) a partir de um número."""
    base = f"978{seed:09d}"
    total = sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(base))
    return base + str((10 - total % 10) % 10)
