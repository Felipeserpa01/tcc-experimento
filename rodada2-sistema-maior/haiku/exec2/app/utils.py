from datetime import datetime

def validate_cpf(cpf: str) -> bool:
    cpf = cpf.replace(".", "").replace("-", "").strip()
    if len(cpf) != 11 or not cpf.isdigit():
        return False
    if cpf == cpf[0] * 11:
        return False

    first_digit = sum(int(cpf[i]) * (10 - i) for i in range(9)) % 11
    first_digit = 0 if first_digit < 2 else 11 - first_digit

    second_digit = sum(int(cpf[i]) * (11 - i) for i in range(10)) % 11
    second_digit = 0 if second_digit < 2 else 11 - second_digit

    return cpf[9] == str(first_digit) and cpf[10] == str(second_digit)

def validate_crm(crm: str) -> bool:
    crm = crm.strip()
    return len(crm) >= 5 and len(crm) <= 10 and crm.isdigit()

def calculate_age(birth_date) -> int:
    today = datetime.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def format_cpf(cpf: str) -> str:
    cpf = cpf.replace(".", "").replace("-", "").strip()
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def format_crm(crm: str, state: str = "SP") -> str:
    return f"{crm}/{state}"
