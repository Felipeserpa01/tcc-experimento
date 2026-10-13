"""Validadores de documentos e dados brasileiros."""

from __future__ import annotations

import re

BRAZILIAN_STATES = frozenset(
    {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
        "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
        "SP", "SE", "TO",
    }
)

_DIGITS_RE = re.compile(r"\D")


def strip_non_digits(value: str) -> str:
    return _DIGITS_RE.sub("", value or "")


# ---------------------------------------------------------------------------
# CPF
# ---------------------------------------------------------------------------
def is_valid_cpf(cpf: str) -> bool:
    """Valida CPF conferindo os dois digitos verificadores."""
    digits = strip_non_digits(cpf)
    if len(digits) != 11:
        return False
    if digits == digits[0] * 11:  # CPFs com todos os digitos iguais sao invalidos
        return False

    for position in (9, 10):
        weight = position + 1
        total = sum(int(digits[i]) * (weight - i) for i in range(position))
        remainder = (total * 10) % 11
        check_digit = 0 if remainder == 10 else remainder
        if check_digit != int(digits[position]):
            return False
    return True


def normalize_cpf(cpf: str) -> str:
    """Retorna o CPF apenas com digitos. Levanta ValueError se invalido."""
    digits = strip_non_digits(cpf)
    if not is_valid_cpf(digits):
        raise ValueError("CPF invalido: verifique os digitos verificadores.")
    return digits


def format_cpf(cpf: str) -> str:
    digits = strip_non_digits(cpf)
    if len(digits) != 11:
        return cpf
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


# ---------------------------------------------------------------------------
# Registro profissional (CRM / COREN)
# ---------------------------------------------------------------------------
def normalize_council_number(number: str) -> str:
    """Numero do conselho: 4 a 7 digitos, sem zeros a esquerda supérfluos."""
    digits = strip_non_digits(number)
    if not digits:
        raise ValueError("Numero do registro profissional e obrigatorio.")
    if not 4 <= len(digits) <= 7:
        raise ValueError("Numero do registro profissional deve ter entre 4 e 7 digitos.")
    if set(digits) == {"0"}:
        raise ValueError("Numero do registro profissional invalido.")
    return digits


def normalize_state(state: str) -> str:
    uf = (state or "").strip().upper()
    if uf not in BRAZILIAN_STATES:
        raise ValueError(f"UF invalida: '{state}'. Use uma das 27 unidades federativas.")
    return uf


def is_valid_crm(number: str, state: str) -> bool:
    try:
        normalize_council_number(number)
        normalize_state(state)
    except ValueError:
        return False
    return True


# ---------------------------------------------------------------------------
# Telefone e CEP
# ---------------------------------------------------------------------------
def normalize_phone(phone: str) -> str:
    """Telefone brasileiro: 10 digitos (fixo) ou 11 (celular), com DDD.

    Aceita o codigo do pais (+55) e o descarta.
    """
    digits = strip_non_digits(phone)
    if len(digits) in (12, 13) and digits.startswith("55"):
        digits = digits[2:]
    if len(digits) not in (10, 11):
        raise ValueError("Telefone deve conter DDD + numero (10 ou 11 digitos).")
    if digits[:2] < "11" or digits[:2] > "99":
        raise ValueError("DDD invalido.")
    if len(digits) == 11 and digits[2] != "9":
        raise ValueError("Celular com 11 digitos deve iniciar com 9 apos o DDD.")
    return digits


def normalize_zip_code(zip_code: str) -> str:
    digits = strip_non_digits(zip_code)
    if len(digits) != 8:
        raise ValueError("CEP deve conter 8 digitos.")
    return digits
