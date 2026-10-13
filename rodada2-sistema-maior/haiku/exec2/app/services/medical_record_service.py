from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import MedicalRecord, Prescription, Exam
from app.schemas import MedicalRecordCreate, PrescriptionCreate, ExamCreate, ExamUpdate
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.repositories.exam_repository import ExamRepository
from app.repositories.appointment_repository import AppointmentRepository

class MedicalRecordService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MedicalRecordRepository(db)
        self.prescription_repo = PrescriptionRepository(db)
        self.exam_repo = ExamRepository(db)
        self.appt_repo = AppointmentRepository(db)

    def create_record(self, record_data: MedicalRecordCreate, user_id: int):
        appointment = self.appt_repo.get_by_id(record_data.appointment_id)
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

        if appointment.medical_record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Record already exists")

        if appointment.professional_id != record_data.doctor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only create record for own appointments")

        record = MedicalRecord(**record_data.dict())
        return self.repo.create(record)

    def get_record(self, record_id: int, user_id: int, user_role: str):
        record = self.repo.get_by_id(record_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

        if user_role == "patient" and record.patient_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return record

    def get_patient_history(self, patient_id: int, skip: int = 0, limit: int = 100):
        return self.repo.get_by_patient(patient_id, skip, limit)

    def add_prescription(self, prescription_data: PrescriptionCreate, user_id: int):
        record = self.repo.get_by_id(prescription_data.medical_record_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

        if record.doctor_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctor can add prescriptions")

        prescription = Prescription(**prescription_data.dict())
        return self.prescription_repo.create(prescription)

    def get_prescriptions(self, record_id: int):
        return self.prescription_repo.get_by_medical_record(record_id)

    def add_exam(self, exam_data: ExamCreate, user_id: int):
        record = self.repo.get_by_id(exam_data.medical_record_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

        if record.doctor_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctor can add exams")

        exam = Exam(**exam_data.dict())
        return self.exam_repo.create(exam)

    def update_exam_result(self, exam_id: int, exam_update: ExamUpdate, user_id: int):
        exam = self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        record = self.repo.get_by_id(exam.medical_record_id)
        if record.doctor_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctor can update results")

        for field, value in exam_update.dict(exclude_unset=True).items():
            setattr(exam, field, value)

        return self.exam_repo.update(exam)

    def get_exams(self, record_id: int):
        return self.exam_repo.get_by_medical_record(record_id)
