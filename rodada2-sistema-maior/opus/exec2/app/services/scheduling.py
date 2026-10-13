"""Regras puras de agenda: janelas de disponibilidade, horários e transições de status.

Não acessam o banco — facilitam testes unitários das regras de negócio.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol

from app.core.exceptions import BusinessRuleError
from app.models.enums import AppointmentStatus

_S = AppointmentStatus

ALLOWED_TRANSITIONS: dict[AppointmentStatus, frozenset[AppointmentStatus]] = {
    _S.SCHEDULED: frozenset({_S.CONFIRMED, _S.IN_PROGRESS, _S.CANCELLED, _S.NO_SHOW}),
    _S.CONFIRMED: frozenset({_S.IN_PROGRESS, _S.CANCELLED, _S.NO_SHOW}),
    _S.IN_PROGRESS: frozenset({_S.COMPLETED}),
    _S.COMPLETED: frozenset(),
    _S.CANCELLED: frozenset(),
    _S.NO_SHOW: frozenset(),
}

STATUS_LABELS = {
    _S.SCHEDULED: "agendada",
    _S.CONFIRMED: "confirmada",
    _S.IN_PROGRESS: "em andamento",
    _S.COMPLETED: "realizada",
    _S.CANCELLED: "cancelada",
    _S.NO_SHOW: "marcada como falta",
}


class AvailabilityWindow(Protocol):
    weekday: int
    start_time: time
    end_time: time
    slot_minutes: int


@dataclass(frozen=True)
class Slot:
    start_at: datetime
    end_at: datetime


def can_transition(current: AppointmentStatus, target: AppointmentStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(current: AppointmentStatus, target: AppointmentStatus) -> None:
    if not can_transition(current, target):
        raise BusinessRuleError(
            f"Não é possível alterar uma consulta {STATUS_LABELS[current]} para '{target.value}'.",
            code="transicao_de_status_invalida",
            details={"status_atual": current.value, "status_desejado": target.value},
        )


def intervals_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Intervalos semiabertos [início, fim) se sobrepõem?"""
    return a_start < b_end and b_start < a_end


def windows_overlap(first: AvailabilityWindow, second: AvailabilityWindow) -> bool:
    return first.weekday == second.weekday and first.start_time < second.end_time and second.start_time < first.end_time


def resolve_slot(windows: Iterable[AvailabilityWindow], start_at: datetime) -> Slot:
    """Encontra a janela de disponibilidade que comporta uma consulta iniciando em ``start_at``.

    Regras: a consulta deve começar dentro de uma janela do dia da semana, alinhada aos
    intervalos da janela (ex.: 08:00, 08:30...) e terminar até o fim da janela.
    """
    day_windows = [w for w in windows if w.weekday == start_at.weekday()]
    for window in day_windows:
        window_start = datetime.combine(start_at.date(), window.start_time)
        window_end = datetime.combine(start_at.date(), window.end_time)
        if not window_start <= start_at < window_end:
            continue
        offset_minutes = int((start_at - window_start).total_seconds() // 60)
        if offset_minutes % window.slot_minutes != 0:
            raise BusinessRuleError(
                f"O horário deve respeitar intervalos de {window.slot_minutes} minutos "
                f"a partir de {window.start_time.strftime('%H:%M')}.",
                code="horario_desalinhado",
            )
        end_at = start_at + timedelta(minutes=window.slot_minutes)
        if end_at > window_end:
            raise BusinessRuleError(
                "A consulta ultrapassaria o fim do período de atendimento do médico.",
                code="fora_da_agenda",
            )
        return Slot(start_at=start_at, end_at=end_at)

    raise BusinessRuleError(
        "O horário solicitado está fora da agenda de disponibilidade do médico.",
        code="fora_da_agenda",
    )


def generate_slots(windows: Iterable[AvailabilityWindow], day: date) -> list[Slot]:
    """Todos os horários possíveis de um dia, segundo as janelas de disponibilidade."""
    slots: list[Slot] = []
    for window in sorted((w for w in windows if w.weekday == day.weekday()), key=lambda w: w.start_time):
        cursor = datetime.combine(day, window.start_time)
        window_end = datetime.combine(day, window.end_time)
        step = timedelta(minutes=window.slot_minutes)
        while cursor + step <= window_end:
            slots.append(Slot(start_at=cursor, end_at=cursor + step))
            cursor += step
    return slots


def free_slots(
    all_slots: Sequence[Slot], busy: Iterable[tuple[datetime, datetime]], not_before: datetime
) -> list[Slot]:
    busy_intervals = list(busy)
    return [
        slot
        for slot in all_slots
        if slot.start_at > not_before
        and not any(intervals_overlap(slot.start_at, slot.end_at, b_start, b_end) for b_start, b_end in busy_intervals)
    ]
