"""Agregador de todas as rotas da API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import appointments, audit, auth, billing, medical_records, patients
from app.api.v1 import professionals, reports, users

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(patients.insurance_router)
api_router.include_router(patients.router)
api_router.include_router(professionals.router)
api_router.include_router(appointments.router)
api_router.include_router(medical_records.appointment_clinical_router)
api_router.include_router(appointments.waitlist_router)
api_router.include_router(medical_records.records_router)
api_router.include_router(medical_records.prescriptions_router)
api_router.include_router(medical_records.exams_router)
api_router.include_router(billing.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
api_router.include_router(audit.notifications_router)
