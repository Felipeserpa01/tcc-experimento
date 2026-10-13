"""Envio de e-mails (SMTP em produção; log em desenvolvimento)."""

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class LoggingEmailSender:
    """Não envia e-mails: apenas registra em log (corpo somente em desenvolvimento)."""

    def __init__(self, include_body: bool = False) -> None:
        self.include_body = include_body

    def send(self, message: EmailMessage) -> None:
        logger.info("E-mail para %s: %s", message.to, message.subject)
        if self.include_body:
            logger.info("Conteúdo: %s", message.body)


class SmtpEmailSender:
    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.sender = sender
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = self.sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.body)
        with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(mime)


@lru_cache
def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.smtp_host:
        return SmtpEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            sender=settings.smtp_from,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
        )
    return LoggingEmailSender(include_body=settings.environment == "development")
