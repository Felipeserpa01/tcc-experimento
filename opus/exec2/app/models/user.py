from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.loan import Loan


class UserRole(enum.StrEnum):
    LIBRARIAN = "librarian"
    READER = "reader"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(60))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda roles: [role.value for role in roles],
        )
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    loans: Mapped[list[Loan]] = relationship(back_populates="reader")
