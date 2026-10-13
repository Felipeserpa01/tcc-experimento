import io
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.exceptions import InvalidInputError, NotFoundError, PayloadTooLargeError, UnsupportedMediaTypeError
from app.services import email as email_module
from app.services.email import EmailMessage, LoggingEmailSender, SmtpEmailSender
from app.services.file_storage import FileStorage, sanitize_filename


class TestSettings:
    def test_secret_key_is_required(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SECRET_KEY")
        with pytest.raises(ValueError, match="secret_key"):
            Settings(_env_file=None)  # type: ignore[call-arg]

    @pytest.mark.parametrize("secret", ["curta", "changeme"])
    def test_weak_secret_is_rejected(self, monkeypatch: pytest.MonkeyPatch, secret: str) -> None:
        monkeypatch.setenv("SECRET_KEY", secret)
        with pytest.raises(ValueError):
            Settings(_env_file=None)  # type: ignore[call-arg]

    def test_invalid_timezone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TIMEZONE", "Marte/Olympus")
        with pytest.raises(ValueError, match="Fuso horário"):
            Settings(_env_file=None)  # type: ignore[call-arg]


class TestFileStorage:
    def test_save_resolve_and_delete(self, tmp_path: Path) -> None:
        storage = FileStorage(base_dir=str(tmp_path), max_size=1024)
        stored = storage.save(io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 10), "foto.png", "image/png", folder="exames")
        assert stored.relative_path.startswith("exames/") and stored.relative_path.endswith(".png")
        assert storage.resolve(stored.relative_path).read_bytes().startswith(b"\x89PNG")
        storage.delete(stored.relative_path)
        with pytest.raises(NotFoundError):
            storage.resolve(stored.relative_path)

    def test_size_limit(self, tmp_path: Path) -> None:
        storage = FileStorage(base_dir=str(tmp_path), max_size=10)
        with pytest.raises(PayloadTooLargeError):
            storage.save(io.BytesIO(b"%PDF-" + b"x" * 20), "grande.pdf", "application/pdf", folder="exames")
        assert list((tmp_path / "exames").iterdir()) == []  # arquivo parcial removido

    def test_empty_and_invalid_files(self, tmp_path: Path) -> None:
        storage = FileStorage(base_dir=str(tmp_path), max_size=1024)
        with pytest.raises(InvalidInputError):
            storage.save(io.BytesIO(b""), "vazio.pdf", "application/pdf", folder="exames")
        with pytest.raises(UnsupportedMediaTypeError):
            storage.save(io.BytesIO(b"GIF89a"), "a.gif", "image/gif", folder="exames")

    def test_path_traversal_is_blocked(self, tmp_path: Path) -> None:
        storage = FileStorage(base_dir=str(tmp_path / "uploads"), max_size=1024)
        (tmp_path / "segredo.txt").write_text("x")
        with pytest.raises(NotFoundError):
            storage.resolve("../segredo.txt")

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("../../etc/passwd", "passwd"),
            ("laudo<script>.pdf", "laudo_script_.pdf"),
            (None, "arquivo"),
            ("...", "arquivo"),
        ],
    )
    def test_sanitize_filename(self, raw: str | None, expected: str) -> None:
        assert sanitize_filename(raw) == expected


class TestEmailSenders:
    def test_logging_sender_hides_body_by_default(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level("INFO")
        LoggingEmailSender().send(EmailMessage(to="a@b.com", subject="Assunto", body="token-secreto"))
        assert "Assunto" in caplog.text
        assert "token-secreto" not in caplog.text

    def test_smtp_sender(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[str] = []

        class FakeSMTP:
            def __init__(self, host: str, port: int, timeout: int) -> None:
                calls.append(f"connect {host}:{port}")

            def __enter__(self) -> "FakeSMTP":
                return self

            def __exit__(self, *args: object) -> None:
                calls.append("quit")

            def starttls(self) -> None:
                calls.append("starttls")

            def login(self, user: str, password: str) -> None:
                calls.append(f"login {user}")

            def send_message(self, message) -> None:
                calls.append(f"send {message['To']}")

        monkeypatch.setattr(email_module.smtplib, "SMTP", FakeSMTP)
        sender = SmtpEmailSender("smtp.exemplo.com", 587, "clinica@exemplo.com", "usuario", "senha")
        sender.send(EmailMessage(to="paciente@exemplo.com", subject="Oi", body="Corpo"))
        assert calls == [
            "connect smtp.exemplo.com:587",
            "starttls",
            "login usuario",
            "send paciente@exemplo.com",
            "quit",
        ]

    def test_factory_selects_sender_from_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.config import get_settings

        email_module.get_email_sender.cache_clear()
        monkeypatch.setenv("SMTP_HOST", "smtp.exemplo.com")
        get_settings.cache_clear()
        try:
            assert isinstance(email_module.get_email_sender(), SmtpEmailSender)
        finally:
            monkeypatch.delenv("SMTP_HOST")
            get_settings.cache_clear()
            email_module.get_email_sender.cache_clear()
        assert isinstance(email_module.get_email_sender(), LoggingEmailSender)
