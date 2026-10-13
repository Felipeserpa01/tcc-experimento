from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import BillingStatus, PaymentMethod


class Billing(Base):
    __tablename__ = "billings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id"), nullable=False, index=True
    )

    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    final_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    status: Mapped[BillingStatus] = mapped_column(
        Enum(BillingStatus), default=BillingStatus.PENDING, nullable=False, index=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    appointment: Mapped["Appointment"] = relationship(back_populates="billings")
