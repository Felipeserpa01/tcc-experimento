"""Funções auxiliares de data e hora."""

from datetime import date, datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.core.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@lru_cache
def _library_timezone() -> ZoneInfo:
    return ZoneInfo(settings.library_timezone)


def local_date(moment: datetime) -> date:
    """Data de calendário de `moment` no fuso horário da biblioteca.

    Datas previstas de devolução e dias de atraso são contados no calendário
    local: um empréstimo feito às 22h em São Paulo pertence àquele dia, mesmo
    que em UTC já seja o dia seguinte.
    """
    if moment.tzinfo is None:
        raise ValueError("É necessário um datetime com fuso horário")
    return moment.astimezone(_library_timezone()).date()
