import re


def clean_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", cpf or "")


def _calculate_digit(cpf_partial: str) -> int:
    weight = len(cpf_partial) + 1
    total = sum(int(digit) * (weight - index) for index, digit in enumerate(cpf_partial))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


def is_valid_cpf(cpf: str) -> bool:
    """Validates a Brazilian CPF using its official check-digit algorithm."""
    digits = clean_cpf(cpf)

    if len(digits) != 11:
        return False
    if digits == digits[0] * 11:
        return False

    first_check = _calculate_digit(digits[:9])
    if first_check != int(digits[9]):
        return False

    second_check = _calculate_digit(digits[:10])
    if second_check != int(digits[10]):
        return False

    return True


def format_cpf(cpf: str) -> str:
    digits = clean_cpf(cpf)
    if len(digits) != 11:
        return cpf
    return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
