"""Fonte única de data/hora da aplicação.

Todas as datas de negócio são armazenadas como ``datetime`` *naive* no fuso horário
da clínica (``TIMEZONE``). Centralizar a obtenção do horário atual facilita testes
(basta substituir ``now``) e evita misturar fusos diferentes.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def clinic_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def now() -> datetime:
    """Data/hora atual no fuso da clínica, sem tzinfo e sem microssegundos."""
    return datetime.now(clinic_timezone()).replace(tzinfo=None, microsecond=0)


def today() -> date:
    return now().date()


def to_clinic_naive(value: datetime) -> datetime:
    """Converte um datetime com fuso para o horário local da clínica (naive)."""
    if value.tzinfo is None:
        return value
    return value.astimezone(clinic_timezone()).replace(tzinfo=None)
