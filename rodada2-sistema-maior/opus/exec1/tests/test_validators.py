"""Testes unitarios dos validadores e da politica de senha."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationFailedError
from app.core.security import (
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.utils.validators import (
    format_cpf,
    is_valid_cpf,
    is_valid_crm,
    normalize_council_number,
    normalize_cpf,
    normalize_phone,
    normalize_state,
    normalize_zip_code,
)


class TestCpf:
    @pytest.mark.parametrize(
        "cpf",
        ["529.982.247-25", "52998224725", "111.444.777-35", "390.533.447-05"],
    )
    def test_accepts_valid_cpf(self, cpf):
        assert is_valid_cpf(cpf) is True

    @pytest.mark.parametrize(
        "cpf",
        [
            "529.982.247-26",  # segundo digito verificador errado
            "52998224715",  # primeiro digito verificador errado
            "111.111.111-11",  # todos os digitos iguais
            "00000000000",
            "1234567890",  # 10 digitos
            "123456789012",  # 12 digitos
            "",
            "abcdefghijk",
        ],
    )
    def test_rejects_invalid_cpf(self, cpf):
        assert is_valid_cpf(cpf) is False

    def test_normalize_strips_mask(self):
        assert normalize_cpf("529.982.247-25") == "52998224725"

    def test_normalize_raises_for_invalid(self):
        with pytest.raises(ValueError):
            normalize_cpf("529.982.247-26")

    def test_format_cpf(self):
        assert format_cpf("52998224725") == "529.982.247-25"


class TestProfessionalRegistration:
    @pytest.mark.parametrize("number", ["1234", "123456", "1234567"])
    def test_valid_council_numbers(self, number):
        assert normalize_council_number(number) == number

    @pytest.mark.parametrize("number", ["123", "12345678", "0000", "", "abc"])
    def test_invalid_council_numbers(self, number):
        with pytest.raises(ValueError):
            normalize_council_number(number)

    def test_crm_requires_valid_state(self):
        assert is_valid_crm("123456", "SP") is True
        assert is_valid_crm("123456", "XX") is False

    def test_normalize_state_uppercases(self):
        assert normalize_state("sp") == "SP"

    def test_normalize_state_rejects_unknown(self):
        with pytest.raises(ValueError):
            normalize_state("ZZ")


class TestContactData:
    @pytest.mark.parametrize(
        "phone,expected",
        [
            ("(11) 98765-4321", "11987654321"),
            ("1133334444", "1133334444"),
            ("+55 11 98765-4321", "5511987654321"[2:]),
        ],
    )
    def test_valid_phones(self, phone, expected):
        assert normalize_phone(phone) == expected

    @pytest.mark.parametrize("phone", ["123", "119876543210", "0987654321", "11887654321"])
    def test_invalid_phones(self, phone):
        with pytest.raises(ValueError):
            normalize_phone(phone)

    def test_zip_code(self):
        assert normalize_zip_code("01001-000") == "01001000"
        with pytest.raises(ValueError):
            normalize_zip_code("123")


class TestPasswordPolicy:
    @pytest.mark.parametrize("password", ["SenhaForte@123", "Abc#12345", "x1!Yzabc"])
    def test_accepts_strong_passwords(self, password):
        assert validate_password_strength(password) == password

    @pytest.mark.parametrize(
        "password,reason",
        [
            ("Ab@1", "curta demais"),
            ("semnumeros@", "sem numeros"),
            ("SemSimbolo123", "sem simbolo"),
            ("12345678!", "sem letras"),
            ("senha123", "senha comum"),
        ],
    )
    def test_rejects_weak_passwords(self, password, reason):
        with pytest.raises(ValidationFailedError):
            validate_password_strength(password)

    def test_hash_and_verify(self):
        hashed = hash_password("SenhaForte@123")
        assert hashed != "SenhaForte@123"
        assert verify_password("SenhaForte@123", hashed) is True
        assert verify_password("SenhaErrada@123", hashed) is False

    def test_hash_is_salted(self):
        assert hash_password("SenhaForte@123") != hash_password("SenhaForte@123")

    def test_verify_handles_garbage_hash(self):
        assert verify_password("SenhaForte@123", "nao-e-um-hash") is False
