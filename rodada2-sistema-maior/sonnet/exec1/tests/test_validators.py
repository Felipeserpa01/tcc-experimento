from app.core.security import validate_password_policy
from app.utils.cpf_validator import is_valid_cpf
from app.utils.crm_validator import is_valid_crm


def test_valid_cpf_accepted():
    assert is_valid_cpf("529.982.247-25") is True


def test_cpf_with_all_same_digits_rejected():
    assert is_valid_cpf("111.111.111-11") is False


def test_cpf_with_wrong_check_digit_rejected():
    assert is_valid_cpf("529.982.247-26") is False


def test_cpf_with_wrong_length_rejected():
    assert is_valid_cpf("123") is False


def test_valid_crm_accepted():
    assert is_valid_crm("123456-SP") is True


def test_crm_with_invalid_uf_rejected():
    assert is_valid_crm("123456-XX") is False


def test_crm_with_wrong_format_rejected():
    assert is_valid_crm("SP-123456") is False


def test_password_policy_accepts_strong_password():
    assert validate_password_policy("Senha123!") is True


def test_password_policy_rejects_short_password():
    assert validate_password_policy("Ab1!") is False


def test_password_policy_rejects_missing_symbol():
    assert validate_password_policy("Senha1234") is False


def test_password_policy_rejects_missing_number():
    assert validate_password_policy("SenhaForte!") is False
