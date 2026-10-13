from dataclasses import dataclass
from datetime import date, datetime, time

import pytest

from app.core.exceptions import BusinessRuleError
from app.core.permissions import Permission, has_permission
from app.models.enums import AppointmentStatus as S
from app.models.enums import Role
from app.services import scheduling


@dataclass
class Window:
    weekday: int
    start_time: time
    end_time: time
    slot_minutes: int = 30


MONDAY = date(2030, 1, 7)
WINDOWS = [Window(0, time(8), time(12)), Window(0, time(14), time(16), 60), Window(2, time(9), time(10))]


class TestStatusTransitions:
    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (S.SCHEDULED, S.CONFIRMED),
            (S.SCHEDULED, S.CANCELLED),
            (S.CONFIRMED, S.IN_PROGRESS),
            (S.CONFIRMED, S.NO_SHOW),
            (S.IN_PROGRESS, S.COMPLETED),
        ],
    )
    def test_allowed(self, current: S, target: S) -> None:
        scheduling.ensure_transition(current, target)

    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (S.COMPLETED, S.CANCELLED),
            (S.CANCELLED, S.CONFIRMED),
            (S.NO_SHOW, S.COMPLETED),
            (S.IN_PROGRESS, S.CANCELLED),
            (S.SCHEDULED, S.COMPLETED),
            (S.CONFIRMED, S.CONFIRMED),
        ],
    )
    def test_blocked(self, current: S, target: S) -> None:
        with pytest.raises(BusinessRuleError) as exc:
            scheduling.ensure_transition(current, target)
        assert exc.value.code == "transicao_de_status_invalida"

    def test_terminal_statuses_have_no_exit(self) -> None:
        for status in (S.COMPLETED, S.CANCELLED, S.NO_SHOW):
            assert not scheduling.ALLOWED_TRANSITIONS[status]


class TestSlotResolution:
    def test_slot_inside_window(self) -> None:
        slot = scheduling.resolve_slot(WINDOWS, datetime(2030, 1, 7, 9, 30))
        assert slot.end_at == datetime(2030, 1, 7, 10, 0)

    def test_slot_uses_window_duration(self) -> None:
        slot = scheduling.resolve_slot(WINDOWS, datetime(2030, 1, 7, 15, 0))
        assert slot.end_at == datetime(2030, 1, 7, 16, 0)

    def test_misaligned_slot(self) -> None:
        with pytest.raises(BusinessRuleError) as exc:
            scheduling.resolve_slot(WINDOWS, datetime(2030, 1, 7, 9, 15))
        assert exc.value.code == "horario_desalinhado"

    @pytest.mark.parametrize(
        "start",
        [
            datetime(2030, 1, 7, 12, 0),  # fim da janela
            datetime(2030, 1, 7, 7, 30),  # antes da janela
            datetime(2030, 1, 8, 9, 0),  # terça: sem agenda
            datetime(2030, 1, 7, 13, 0),  # intervalo de almoço
        ],
    )
    def test_outside_availability(self, start: datetime) -> None:
        with pytest.raises(BusinessRuleError) as exc:
            scheduling.resolve_slot(WINDOWS, start)
        assert exc.value.code == "fora_da_agenda"

    def test_slot_cannot_overflow_window(self) -> None:
        windows = [Window(0, time(8), time(9, 15), 30)]
        with pytest.raises(BusinessRuleError, match="ultrapassaria"):
            scheduling.resolve_slot(windows, datetime(2030, 1, 7, 9, 0))


class TestSlotGeneration:
    def test_generate_slots_for_day(self) -> None:
        slots = scheduling.generate_slots(WINDOWS, MONDAY)
        assert len(slots) == 8 + 2
        assert slots[0].start_at == datetime(2030, 1, 7, 8, 0)
        assert slots[-1].start_at == datetime(2030, 1, 7, 15, 0)

    def test_no_slots_on_day_without_availability(self) -> None:
        assert scheduling.generate_slots(WINDOWS, date(2030, 1, 8)) == []

    def test_free_slots_excludes_busy_and_past(self) -> None:
        slots = scheduling.generate_slots(WINDOWS, MONDAY)
        busy = [(datetime(2030, 1, 7, 10, 0), datetime(2030, 1, 7, 10, 30))]
        free = scheduling.free_slots(slots, busy, not_before=datetime(2030, 1, 7, 9, 0))
        starts = [s.start_at.time() for s in free]
        assert time(9, 0) not in starts  # não é posterior ao "agora"
        assert time(10, 0) not in starts  # ocupado
        assert time(9, 30) in starts and time(10, 30) in starts

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            ((9, 0, 9, 30), (9, 30, 10, 0), False),  # adjacentes não conflitam
            ((9, 0, 10, 0), (9, 30, 10, 30), True),
            ((9, 0, 10, 0), (9, 15, 9, 45), True),
        ],
    )
    def test_intervals_overlap(self, a: tuple, b: tuple, expected: bool) -> None:
        def dt(h: int, m: int) -> datetime:
            return datetime(2030, 1, 7, h, m)

        assert scheduling.intervals_overlap(dt(a[0], a[1]), dt(a[2], a[3]), dt(b[0], b[1]), dt(b[2], b[3])) is expected

    def test_windows_overlap(self) -> None:
        assert scheduling.windows_overlap(Window(0, time(8), time(12)), Window(0, time(11), time(13)))
        assert not scheduling.windows_overlap(Window(0, time(8), time(12)), Window(0, time(12), time(13)))
        assert not scheduling.windows_overlap(Window(0, time(8), time(12)), Window(1, time(8), time(12)))


class TestPermissionMatrix:
    @pytest.mark.parametrize(
        ("role", "permission", "expected"),
        [
            (Role.ADMIN, Permission.USERS_MANAGE, True),
            (Role.ADMIN, Permission.CLINICAL_WRITE, False),
            (Role.ADMIN, Permission.CLINICAL_READ, False),
            (Role.RECEPTIONIST, Permission.BILLING_MANAGE, True),
            (Role.RECEPTIONIST, Permission.CLINICAL_READ, False),
            (Role.RECEPTIONIST, Permission.REPORTS_READ, False),
            (Role.DOCTOR, Permission.CLINICAL_WRITE, True),
            (Role.DOCTOR, Permission.BILLING_MANAGE, False),
            (Role.NURSE, Permission.CLINICAL_READ, True),
            (Role.NURSE, Permission.CLINICAL_WRITE, False),
            (Role.NURSE, Permission.APPOINTMENTS_CREATE, False),
            (Role.PATIENT, Permission.APPOINTMENTS_CREATE, True),
            (Role.PATIENT, Permission.PATIENTS_CREATE, False),
            (Role.PATIENT, Permission.REPORTS_READ, False),
            (Role.PATIENT, Permission.AUDIT_READ, False),
        ],
    )
    def test_role_permissions(self, role: Role, permission: Permission, expected: bool) -> None:
        assert has_permission(role, permission) is expected
