def normalize_isbn(value: str) -> str:
    """Remove hífens/espaços e valida um ISBN-10 ou ISBN-13 (incluindo o dígito verificador).

    Retorna o ISBN normalizado ou lança ValueError.
    """
    isbn = value.replace("-", "").replace(" ", "").upper()

    if len(isbn) == 10:
        if not (isbn[:9].isdigit() and (isbn[9].isdigit() or isbn[9] == "X")):
            raise ValueError("ISBN-10 deve conter 9 dígitos seguidos de um dígito ou 'X'")
        digits = [10 if c == "X" else int(c) for c in isbn]
        if sum((10 - i) * d for i, d in enumerate(digits)) % 11 != 0:
            raise ValueError("Dígito verificador do ISBN-10 inválido")
        return isbn

    if len(isbn) == 13:
        if not isbn.isdigit():
            raise ValueError("ISBN-13 deve conter apenas dígitos")
        total = sum((3 if i % 2 else 1) * int(c) for i, c in enumerate(isbn))
        if total % 10 != 0:
            raise ValueError("Dígito verificador do ISBN-13 inválido")
        return isbn

    raise ValueError("ISBN deve ter 10 ou 13 caracteres (desconsiderando hífens)")
