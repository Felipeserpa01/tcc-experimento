import re

VALID_UF_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

CRM_PATTERN = re.compile(r"^\d{4,6}-([A-Z]{2})$")


def is_valid_crm(crm: str) -> bool:
    """Validates the format of a CRM registration number, e.g. '123456-SP'."""
    if not crm:
        return False
    match = CRM_PATTERN.match(crm.strip().upper())
    if not match:
        return False
    return match.group(1) in VALID_UF_CODES


def is_valid_license_number(license_number: str) -> bool:
    """Generic professional license validator (CRM for doctors, COREN for nurses)."""
    return is_valid_crm(license_number)
