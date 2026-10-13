"""Validação e normalização de ISBN-10 e ISBN-13."""

import re

_SEPARATORS = re.compile(r"[\s-]")
_ISBN10 = re.compile(r"[0-9]{9}[0-9X]")
_ISBN13 = re.compile(r"97[89][0-9]{10}")


def isbn13_check_digit(first_12_digits: str) -> str:
    total = sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(first_12_digits))
    return str((10 - total % 10) % 10)


def _isbn10_is_valid(isbn: str) -> bool:
    if not _ISBN10.fullmatch(isbn):
        return False
    total = sum((10 - i) * (10 if ch == "X" else int(ch)) for i, ch in enumerate(isbn))
    return total % 11 == 0


def normalize_isbn(value: str) -> str:
    """Valida um ISBN-10 ou ISBN-13 e o devolve como ISBN-13, sem separadores.

    Converter tudo para ISBN-13 garante que a mesma obra não seja cadastrada
    duas vezes só por ter sido informada em formatos diferentes.

    Raises:
        ValueError: se o ISBN for inválido.
    """
    cleaned = _SEPARATORS.sub("", value).upper()

    if len(cleaned) == 10:
        if not _isbn10_is_valid(cleaned):
            raise ValueError("ISBN-10 inválido")
        body = "978" + cleaned[:9]
        return body + isbn13_check_digit(body)

    if len(cleaned) == 13:
        if not _ISBN13.fullmatch(cleaned) or cleaned[-1] != isbn13_check_digit(cleaned[:12]):
            raise ValueError("ISBN-13 inválido")
        return cleaned

    raise ValueError("O ISBN deve ter 10 ou 13 dígitos")
