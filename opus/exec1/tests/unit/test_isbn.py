import pytest

from app.core.isbn import normalize_isbn


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9780306406157", "9780306406157"),
        ("978-0-13-235088-4", "9780132350884"),
        ("0306406152", "0306406152"),
        ("0-8044-2957-x", "080442957X"),
        (" 978 0306 40615 7 ", "9780306406157"),
    ],
)
def test_valid_isbns_are_normalized(raw: str, expected: str):
    assert normalize_isbn(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "9780306406158",  # dígito verificador errado (ISBN-13)
        "0306406153",  # dígito verificador errado (ISBN-10)
        "97803064061",  # tamanho inválido
        "97803064061AB",  # letras no ISBN-13
        "X306406152",  # 'X' fora da última posição
        "",
    ],
)
def test_invalid_isbns_raise_value_error(raw: str):
    with pytest.raises(ValueError):
        normalize_isbn(raw)
