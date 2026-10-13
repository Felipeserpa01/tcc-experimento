"""Funções auxiliares de texto usadas nas buscas."""

import unicodedata

LIKE_ESCAPE_CHAR = "\\"


def normalize_text(value: str | None) -> str | None:
    """Remove acentos e aplica casefold, permitindo buscas que ignoram caixa e acentuação."""
    if value is None:
        return None
    decomposed = unicodedata.normalize("NFKD", str(value))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def contains_pattern(term: str) -> str:
    """Padrão LIKE do tipo "contém", com os curingas do termo escapados."""
    escaped = (
        normalize_text(term)
        .replace(LIKE_ESCAPE_CHAR, LIKE_ESCAPE_CHAR * 2)
        .replace("%", LIKE_ESCAPE_CHAR + "%")
        .replace("_", LIKE_ESCAPE_CHAR + "_")
    )
    return f"%{escaped}%"
