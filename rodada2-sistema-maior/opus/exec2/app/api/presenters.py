"""Montagem de respostas compostas a partir de entidades do domínio."""

from app.models.appointment import Appointment
from app.models.patient import Patient
from app.schemas.clinical import (
    ClinicalHistoryEntry,
    ClinicalHistoryOut,
    ExamOut,
    MedicalRecordOut,
    PrescriptionOut,
)
from app.schemas.patient import AllergyOut, PatientSummary


def build_clinical_history(patient: Patient, appointments: list[Appointment]) -> ClinicalHistoryOut:
    entries = [
        ClinicalHistoryEntry(
            appointment_id=appointment.id,
            start_at=appointment.start_at,
            status=appointment.status,
            professional_id=appointment.professional_id,
            professional_name=appointment.professional_name,
            specialty=appointment.specialty,
            reason=appointment.reason,
            medical_record=(
                MedicalRecordOut.model_validate(appointment.medical_record) if appointment.medical_record else None
            ),
            prescriptions=[PrescriptionOut.model_validate(p) for p in appointment.prescriptions],
            exams=[ExamOut.model_validate(e) for e in appointment.exams],
        )
        for appointment in appointments
    ]
    return ClinicalHistoryOut(
        patient=PatientSummary.model_validate(patient),
        allergies=[AllergyOut.model_validate(a) for a in patient.allergies or []],
        total_appointments=len(entries),
        total_prescriptions=sum(len(e.prescriptions) for e in entries),
        total_exams=sum(len(e.exams) for e in entries),
        entries=entries,
    )
