"""Report/indicator schemas."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class AppointmentsByPeriodItem(BaseModel):
    data: date
    total: int


class AppointmentsByProfessionalItem(BaseModel):
    professional_id: int
    professional_nome: str
    total: int


class AppointmentsBySpecialtyItem(BaseModel):
    especialidade: str
    total: int


class AppointmentsByStatusItem(BaseModel):
    status: str
    total: int


class RevenueByPeriodItem(BaseModel):
    data: date
    total: Decimal


class RevenueByPaymentMethodItem(BaseModel):
    forma_pagamento: str
    total: Decimal


class NoShowRateItem(BaseModel):
    professional_id: int
    professional_nome: str
    total_consultas: int
    total_faltas: int
    taxa_faltas: float


class TopPatientItem(BaseModel):
    patient_id: int
    patient_nome: str
    total_consultas: int
