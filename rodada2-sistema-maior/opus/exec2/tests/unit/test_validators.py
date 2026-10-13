from datetime import date

import pytest

from app.utils import validators as v


class TestCPF:
    @pytest.mark.parametrize("cpf", ["529.982.247-25", "52998224725", "111.444.777-35"])
    def test_valid_cpfs_are_normalized_to_digits(self, cpf: str) -> None:
        assert v.normalize_cpf(cpf) == cpf.replace(".", "").replace("-", "")

    @pytest.mark.parametrize("cpf", ["529.982.247-24", "52998224735", "12345678900"])
    def test_invalid_check_digits(self, cpf: str) -> None:
        with pytest.raises(ValueError, match="dígitos verificadores"):
            v.normalize_cpf(cpf)

    @pytest.mark.parametrize("cpf", ["000.000.000-00", "11111111111", "99999999999"])
    def test_repeated_digits_are_rejected(self, cpf: str) -> None:
        assert v.is_valid_cpf(cpf) is False

    @pytest.mark.parametrize("cpf", ["1234567890", "529.982.247-2", "abc.def.ghi-jk", "529 982 247 25", ""])
    def test_invalid_format(self, cpf: str) -> None:
        with pytest.raises(ValueError, match="11 dígitos"):
            v.normalize_cpf(cpf)


class TestCouncilRegistration:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("CRM/SP 123456", "CRM/SP 123456"),
            ("crm-rj 1234", "CRM/RJ 1234"),
            ("123456/MG", "CRM/MG 123456"),
            ("123.456-SP", "CRM/SP 123456"),
            ("CRM SP 000123", "CRM/SP 123"),
        ],
    )
    def test_crm_normalization(self, raw: str, expected: str) -> None:
        assert v.normalize_crm(raw) == expected

    @pytest.mark.parametrize("raw", ["CRM/XX 123456", "CRM/SP 1234567", "CRM/SP", "SP", "CRM/SP 000000", "ABC 123"])
    def test_invalid_crm(self, raw: str) -> None:
        with pytest.raises(ValueError):
            v.normalize_crm(raw)

    def test_coren_normalization(self) -> None:
        assert v.normalize_coren("coren-sp 1234567") == "COREN/SP 1234567"
        with pytest.raises(ValueError):
            v.normalize_coren("CRM/SP 123")


class TestPasswordPolicy:
    def test_strong_password(self) -> None:
        assert v.validate_password_strength("Senha@123") == "Senha@123"

    @pytest.mark.parametrize(
        ("password", "fragment"),
        [
            ("Ab@1", "mínimo 8"),
            ("12345678@", "uma letra"),
            ("Senha@abc", "um número"),
            ("Senha1234", "um símbolo"),
            ("Á" * 40 + "1!", "72 bytes"),
        ],
    )
    def test_weak_passwords(self, password: str, fragment: str) -> None:
        with pytest.raises(ValueError, match=fragment):
            v.validate_password_strength(password)

    def test_all_violations_reported_together(self) -> None:
        assert len(v.password_policy_violations("abc")) == 3


class TestContactData:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("(11) 98765-4321", "11987654321"),
            ("+55 11 98765-4321", "11987654321"),
            ("(21) 3333-4444", "2133334444"),
        ],
    )
    def test_phone_normalization(self, raw: str, expected: str) -> None:
        assert v.normalize_phone(raw) == expected

    @pytest.mark.parametrize(
        "raw", ["98765-4321", "(11) 88765-4321", "(01) 98765-4321", "(11) 9876x-4321", "(11) 6333-4444"]
    )
    def test_invalid_phones(self, raw: str) -> None:
        with pytest.raises(ValueError):
            v.normalize_phone(raw)

    def test_cep_and_state(self) -> None:
        assert v.normalize_cep("01310-100") == "01310100"
        assert v.normalize_state("sp") == "SP"
        with pytest.raises(ValueError):
            v.normalize_cep("0131-100")
        with pytest.raises(ValueError):
            v.normalize_state("XX")


class TestPersonalData:
    @pytest.mark.parametrize("name", ["Maria  da   Silva", "João D'Ávila", "Ana-Maria Souza", "José Jr."])
    def test_valid_names(self, name: str) -> None:
        assert "  " not in v.validate_person_name(name)

    @pytest.mark.parametrize("name", ["Maria 123", "Jo", "@@@", "Ana_Maria"])
    def test_invalid_names(self, name: str) -> None:
        with pytest.raises(ValueError):
            v.validate_person_name(name)

    def test_birth_date_rules(self) -> None:
        assert v.validate_birth_date(date(1990, 1, 1)) == date(1990, 1, 1)
        with pytest.raises(ValueError, match="futuro"):
            v.validate_birth_date(date(2031, 1, 1))  # relógio congelado em 2030
        with pytest.raises(ValueError, match="130"):
            v.validate_birth_date(date(1890, 1, 1))

    @pytest.mark.parametrize(("raw", "expected"), [("j45", "J45"), ("J45.9", "J45.9"), ("i109", "I10.9")])
    def test_icd10(self, raw: str, expected: str) -> None:
        assert v.normalize_icd10(raw) == expected

    def test_invalid_icd10(self) -> None:
        with pytest.raises(ValueError):
            v.normalize_icd10("U999")
