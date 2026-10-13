import re


def validate_cpf(cpf: str) -> bool:
    """Validate Brazilian CPF with check digits."""
    cpf = re.sub(r'\D', '', cpf)

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    # First check digit
    sum_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digit_1 = 11 - (sum_1 % 11)
    digit_1 = 0 if digit_1 >= 10 else digit_1

    if int(cpf[9]) != digit_1:
        return False

    # Second check digit
    sum_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digit_2 = 11 - (sum_2 % 11)
    digit_2 = 0 if digit_2 >= 10 else digit_2

    if int(cpf[10]) != digit_2:
        return False

    return True


def validate_crm(crm: str) -> bool:
    """Validate Brazilian CRM (medical license) format: NNNNNN/UF"""
    valid_states = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO"
    }

    match = re.match(r'^(\d{4,6})/([A-Z]{2})$', crm.strip())

    if not match:
        return False

    state = match.group(2)
    return state in valid_states


def validate_password_strength(password: str) -> bool:
    """Validate password strength: min 8 chars, letters, numbers, symbol."""
    if len(password) < 8:
        return False

    has_letter = bool(re.search(r'[a-zA-Z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_symbol = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))

    return has_letter and has_digit and has_symbol
