"""Domain validators: CPF, CRM and password strength."""
import re


def clean_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def is_valid_cpf(cpf: str) -> bool:
    """Validates a Brazilian CPF number using its two check digits."""
    digits = clean_digits(cpf)
    if len(digits) != 11:
        return False
    if digits == digits[0] * 11:
        return False

    def check_digit(partial: str) -> int:
        weight = len(partial) + 1
        total = sum(int(d) * (weight - i) for i, d in enumerate(partial))
        remainder = (total * 10) % 11
        return 0 if remainder == 10 else remainder

    d1 = check_digit(digits[:9])
    d2 = check_digit(digits[:9] + str(d1))
    return digits[-2:] == f"{d1}{d2}"


def format_cpf(cpf: str) -> str:
    digits = clean_digits(cpf)
    return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


CRM_PATTERN = re.compile(r"^\d{4,6}-[A-Z]{2}$")


def is_valid_crm(crm: str) -> bool:
    """Validates CRM format: 4 to 6 digits, dash, 2-letter state abbreviation. E.g. 123456-SP."""
    if not crm:
        return False
    return bool(CRM_PATTERN.match(crm.strip().upper()))


PASSWORD_PATTERN = re.compile(
    r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+\[\]{};:,.<>?/\\|`~\"'])[^\s]{8,}$"
)


def is_strong_password(password: str) -> bool:
    """At least 8 chars, letters, numbers and at least one symbol."""
    if not password or len(password) < 8:
        return False
    return bool(PASSWORD_PATTERN.match(password))
