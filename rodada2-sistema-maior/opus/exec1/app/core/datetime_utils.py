"""Utilitarios de data/hora.

Convencao do projeto: todos os `datetime` persistidos e manipulados sao
*naive* e representam o horario local da clinica (config `TIMEZONE`).
Isso evita comparacoes entre datas com e sem timezone, que sao a origem
mais comum de bugs em agendamento.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import get_settings


def clinic_timezone() -> ZoneInfo:
    settings = get_settings()
    try:
        return ZoneInfo(settings.timezone)
    except (ZoneInfoNotFoundError, ValueError):  # pragma: no cover - fallback defensivo
        return ZoneInfo("UTC")


def now() -> datetime:
    """Horario atual da clinica, sem timezone (naive)."""
    return datetime.now(tz=clinic_timezone()).replace(tzinfo=None, microsecond=0)


def today() -> date:
    return now().date()


def to_naive_local(value: datetime) -> datetime:
    """Normaliza um datetime recebido da API para o horario local naive."""
    if value.tzinfo is not None:
        value = value.astimezone(clinic_timezone()).replace(tzinfo=None)
    return value.replace(microsecond=0)


def combine(day: date, moment: time) -> datetime:
    return datetime.combine(day, moment).replace(microsecond=0)


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """Intervalo [inicio, fim) que cobre o dia inteiro."""
    start = datetime.combine(day, time.min)
    return start, start + timedelta(days=1)


def range_bounds(start_date: date | None, end_date: date | None) -> tuple[datetime | None, datetime | None]:
    """Converte um intervalo de datas (inclusivo) em limites de datetime."""
    start = datetime.combine(start_date, time.min) if start_date else None
    end = datetime.combine(end_date, time.min) + timedelta(days=1) if end_date else None
    return start, end


def overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and end_a > start_b


def format_minutes(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours}h{rest:02d}min"
    if hours:
        return f"{hours}h"
    return f"{rest}min"
