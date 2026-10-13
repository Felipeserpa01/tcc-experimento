from datetime import timedelta
from decimal import Decimal

import jwt
import pytest

from app.core import security
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.utils.money import apply_discount, to_money


class TestMoney:
    def test_to_money_rounds_half_up(self) -> None:
        assert to_money("10.005") == Decimal("10.01")
        assert to_money(Decimal("10.004")) == Decimal("10.00")

    @pytest.mark.parametrize(
        ("gross", "percent", "discount", "net"),
        [
            ("200.00", "20", "40.00", "160.00"),
            ("199.99", "15", "30.00", "169.99"),
            ("150.00", "0", "0.00", "150.00"),
            ("150.00", "100", "150.00", "0.00"),
            ("99.90", "12.5", "12.49", "87.41"),
        ],
    )
    def test_apply_discount(self, gross: str, percent: str, discount: str, net: str) -> None:
        result = apply_discount(Decimal(gross), Decimal(percent))
        assert result.discount == Decimal(discount)
        assert result.net == Decimal(net)
        assert result.discount + result.net == result.gross

    @pytest.mark.parametrize(("gross", "percent"), [("0", "10"), ("-5", "10"), ("100", "101"), ("100", "-1")])
    def test_invalid_discount_inputs(self, gross: str, percent: str) -> None:
        with pytest.raises(ValueError):
            apply_discount(Decimal(gross), Decimal(percent))


class TestPasswordHashing:
    def test_hash_and_verify(self) -> None:
        hashed = security.hash_password("Senha@123")
        assert hashed != "Senha@123"
        assert security.verify_password("Senha@123", hashed)
        assert not security.verify_password("Senha@124", hashed)

    def test_same_password_generates_different_hashes(self) -> None:
        assert security.hash_password("Senha@123") != security.hash_password("Senha@123")

    def test_verify_never_raises_on_bad_input(self) -> None:
        assert security.verify_password("x" * 100, security.hash_password("Senha@123")) is False
        assert security.verify_password("Senha@123", "hash-corrompido") is False


class TestTokens:
    def test_access_token_roundtrip(self) -> None:
        issued = security.create_access_token(42, "medico", 3)
        payload = security.decode_token(issued.token, security.ACCESS_TOKEN_TYPE)
        assert payload["sub"] == 42
        assert payload["role"] == "medico"
        assert payload["ver"] == 3
        assert issued.expires_in == get_settings().access_token_expire_minutes * 60

    def test_refresh_token_cannot_be_used_as_access_token(self) -> None:
        issued = security.create_refresh_token(1, 0)
        with pytest.raises(AuthenticationError, match="Tipo de token"):
            security.decode_token(issued.token, security.ACCESS_TOKEN_TYPE)

    def test_tampered_token_is_rejected(self) -> None:
        token = security.create_access_token(1, "administrador", 0).token
        forged = jwt.encode(
            jwt.decode(token, options={"verify_signature": False}), "outra-chave-qualquer-com-32-chars!!"
        )
        with pytest.raises(AuthenticationError, match="inválido"):
            security.decode_token(forged, security.ACCESS_TOKEN_TYPE)

    def test_expired_token_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        issued = security._issue({"sub": "1"}, timedelta(seconds=-1), security.ACCESS_TOKEN_TYPE)
        with pytest.raises(AuthenticationError) as exc:
            security.decode_token(issued.token, security.ACCESS_TOKEN_TYPE)
        assert exc.value.code == "token_expirado"

    def test_none_algorithm_is_rejected(self) -> None:
        payload = jwt.decode(
            security.create_access_token(1, "administrador", 0).token, options={"verify_signature": False}
        )
        unsigned = jwt.encode(payload, key=None, algorithm="none")
        with pytest.raises(AuthenticationError):
            security.decode_token(unsigned, security.ACCESS_TOKEN_TYPE)

    def test_opaque_token_hash_is_deterministic(self) -> None:
        token = security.generate_opaque_token()
        assert len(token) >= 40
        assert security.hash_opaque_token(token) == security.hash_opaque_token(token)
        assert security.hash_opaque_token(token) != token
