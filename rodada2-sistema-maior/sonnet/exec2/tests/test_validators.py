"""Unit tests for CPF, CRM and password-strength validators."""
from app.core.validators import is_strong_password, is_valid_cpf, is_valid_crm


class TestCPFValidation:
    def test_valid_cpf_accepted(self):
        assert is_valid_cpf("529.982.247-25") is True
        assert is_valid_cpf("52998224725") is True

    def test_cpf_with_all_same_digits_rejected(self):
        assert is_valid_cpf("111.111.111-11") is False
        assert is_valid_cpf("00000000000") is False

    def test_cpf_with_wrong_check_digits_rejected(self):
        assert is_valid_cpf("529.982.247-26") is False

    def test_cpf_with_wrong_length_rejected(self):
        assert is_valid_cpf("123456789") is False
        assert is_valid_cpf("123456789012") is False

    def test_empty_cpf_rejected(self):
        assert is_valid_cpf("") is False
        assert is_valid_cpf(None) is False


class TestCRMValidation:
    def test_valid_crm_accepted(self):
        assert is_valid_crm("123456-SP") is True
        assert is_valid_crm("1234-RJ") is True

    def test_lowercase_state_accepted(self):
        assert is_valid_crm("123456-sp") is True

    def test_crm_without_state_rejected(self):
        assert is_valid_crm("123456") is False

    def test_crm_without_dash_rejected(self):
        assert is_valid_crm("123456SP") is False

    def test_empty_crm_rejected(self):
        assert is_valid_crm("") is False


class TestPasswordStrength:
    def test_strong_password_accepted(self):
        assert is_strong_password("SenhaForte123!") is True

    def test_short_password_rejected(self):
        assert is_strong_password("Abc1!") is False

    def test_password_without_symbol_rejected(self):
        assert is_strong_password("SenhaForte123") is False

    def test_password_without_number_rejected(self):
        assert is_strong_password("SenhaForte!!!") is False

    def test_password_without_letter_rejected(self):
        assert is_strong_password("12345678!") is False

    def test_password_with_whitespace_rejected(self):
        assert is_strong_password("Senha Forte 123!") is False
