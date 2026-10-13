"""Validadores de dados brasileiros e regras de formato.

Cada função recebe o valor bruto, valida e retorna o valor normalizado, ou
lança ``ValueError`` com uma mensagem clara (em português).
"""

import re
from datetime import date

from app.core import clock

BRAZILIAN_STATES = frozenset(
    {
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    }
)

_CPF_FORMAT_RE = re.compile(r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$")
_CEP_RE = re.compile(r"^\d{5}-?\d{3}$")
_PHONE_CHARS_RE = re.compile(r"^[\d\s()+.-]+$")
_NAME_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[ '.-]+[A-Za-zÀ-ÖØ-öø-ÿ]+)*\.?$")
_ICD10_RE = re.compile(r"^([A-TV-Z]\d{2})(?:\.?(\d{1,2}))?$")
_ANS_RE = re.compile(r"^\d{6}$")

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # limite do bcrypt


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


# --------------------------------------------------------------------------- CPF
def is_valid_cpf(value: str) -> bool:
    """Valida o CPF pelos dois dígitos verificadores (módulo 11)."""
    digits = only_digits(value)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    for position in (9, 10):
        total = sum(int(digits[i]) * (position + 1 - i) for i in range(position))
        check_digit = (total * 10) % 11 % 10
        if check_digit != int(digits[position]):
            return False
    return True


def normalize_cpf(value: str) -> str:
    value = value.strip()
    if not _CPF_FORMAT_RE.match(value):
        raise ValueError("CPF deve conter 11 dígitos (com ou sem pontuação: 000.000.000-00).")
    if not is_valid_cpf(value):
        raise ValueError("CPF inválido: dígitos verificadores não conferem.")
    return only_digits(value)


# --------------------------------------------------------------------------- Conselhos (CRM / COREN)
def _normalize_council_registration(value: str, council: str, max_digits: int) -> str:
    raw = value.strip().upper().replace(".", "")
    prefix = re.compile(rf"^{council}\s*[/-]?\s*([A-Z]{{2}})\s*[/-]?\s*(\d{{1,{max_digits}}})$")
    suffix = re.compile(rf"^(?:{council}\s*)?(\d{{1,{max_digits}}})\s*[/-]?\s*([A-Z]{{2}})$")

    if match := prefix.match(raw):
        state, number = match.group(1), match.group(2)
    elif match := suffix.match(raw):
        number, state = match.group(1), match.group(2)
    else:
        raise ValueError(
            f"{council} em formato inválido. Use '{council}/UF 123456' ou '123456/UF' (até {max_digits} dígitos)."
        )
    if state not in BRAZILIAN_STATES:
        raise ValueError(f"UF do {council} inválida: {state}.")
    if int(number) == 0:
        raise ValueError(f"Número do {council} inválido.")
    return f"{council}/{state} {int(number)}"


def normalize_crm(value: str) -> str:
    """Valida e normaliza o CRM para o formato ``CRM/UF NUMERO``."""
    return _normalize_council_registration(value, "CRM", max_digits=6)


def normalize_coren(value: str) -> str:
    """Valida e normaliza o COREN para o formato ``COREN/UF NUMERO``."""
    return _normalize_council_registration(value, "COREN", max_digits=8)


# --------------------------------------------------------------------------- Senha
def password_policy_violations(password: str) -> list[str]:
    violations: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        violations.append(f"ter no mínimo {MIN_PASSWORD_LENGTH} caracteres")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        violations.append(f"ter no máximo {MAX_PASSWORD_BYTES} bytes")
    if not any(ch.isalpha() for ch in password):
        violations.append("conter ao menos uma letra")
    if not any(ch.isdigit() for ch in password):
        violations.append("conter ao menos um número")
    if not any(not ch.isalnum() and not ch.isspace() for ch in password):
        violations.append("conter ao menos um símbolo (ex.: ! @ # $ %)")
    return violations


def validate_password_strength(password: str) -> str:
    violations = password_policy_violations(password)
    if violations:
        raise ValueError("A senha deve " + ", ".join(violations) + ".")
    return password


# --------------------------------------------------------------------------- Contato / endereço
def normalize_phone(value: str) -> str:
    """Telefone brasileiro com DDD: fixo (10 dígitos) ou celular (11 dígitos, iniciando em 9)."""
    if not _PHONE_CHARS_RE.match(value.strip()):
        raise ValueError("Telefone contém caracteres inválidos.")
    digits = only_digits(value)
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) not in (10, 11):
        raise ValueError("Telefone deve ter DDD + número (10 ou 11 dígitos).")
    if digits[0] == "0" or digits[1] == "0":
        raise ValueError("DDD inválido.")
    if len(digits) == 11 and digits[2] != "9":
        raise ValueError("Celular com 11 dígitos deve começar com 9 após o DDD.")
    if len(digits) == 10 and digits[2] not in "2345":
        raise ValueError("Telefone fixo deve começar com 2, 3, 4 ou 5 após o DDD.")
    return digits


def normalize_cep(value: str) -> str:
    value = value.strip()
    if not _CEP_RE.match(value):
        raise ValueError("CEP deve conter 8 dígitos (00000-000).")
    return only_digits(value)


def normalize_state(value: str) -> str:
    state = value.strip().upper()
    if state not in BRAZILIAN_STATES:
        raise ValueError("UF inválida.")
    return state


def validate_person_name(value: str) -> str:
    name = re.sub(r"\s+", " ", value.strip())
    if not _NAME_RE.match(name):
        raise ValueError("Nome deve conter apenas letras, espaços, apóstrofos, pontos ou hífens.")
    if sum(ch.isalpha() for ch in name) < 3:
        raise ValueError("Nome deve conter ao menos 3 letras.")
    return name


def validate_birth_date(value: date) -> date:
    today = clock.today()
    if value > today:
        raise ValueError("Data de nascimento não pode estar no futuro.")
    if today.year - value.year > 130:
        raise ValueError("Data de nascimento inválida (mais de 130 anos).")
    return value


def normalize_icd10(value: str) -> str:
    """Código CID-10 (ex.: J45 ou J45.9)."""
    match = _ICD10_RE.match(value.strip().upper())
    if not match:
        raise ValueError("Código CID-10 inválido (ex.: J45 ou J45.9).")
    category, subcategory = match.groups()
    return f"{category}.{subcategory}" if subcategory else category


def validate_ans_code(value: str) -> str:
    code = value.strip()
    if not _ANS_RE.match(code):
        raise ValueError("Registro ANS deve conter 6 dígitos.")
    return code
