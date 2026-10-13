import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.loan import Loan


class UserRole(str, enum.Enum):
    LIBRARIAN = "librarian"
    READER = "reader"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.READER,
    )

    loans: Mapped[list["Loan"]] = relationship(back_populates="reader")

    @property
    def is_librarian(self) -> bool:
        return self.role == UserRole.LIBRARIAN
