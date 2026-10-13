from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text, Date, Time, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    RECEPTIONIST = "receptionist"
    PATIENT = "patient"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(Enum(UserRole))
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="user", uselist=False)
    professional = relationship("Professional", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    cpf = Column(String, unique=True, index=True)
    date_of_birth = Column(Date)
    sex = Column(String)
    phone = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    insurance_plan = Column(String, nullable=True)
    allergies = Column(Text, nullable=True)
    observations = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    medical_records = relationship("MedicalRecord", back_populates="patient")
    charges = relationship("Charge", back_populates="patient")

class Professional(Base):
    __tablename__ = "professionals"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    registration_number = Column(String, unique=True, index=True)
    specialization = Column(String)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="professional")
    appointments = relationship("Appointment", back_populates="professional")
    availability_schedules = relationship("AvailabilitySchedule", back_populates="professional")
    medical_records = relationship("MedicalRecord", back_populates="doctor")

class AvailabilitySchedule(Base):
    __tablename__ = "availability_schedules"
    id = Column(Integer, primary_key=True)
    professional_id = Column(Integer, ForeignKey("professionals.id"))
    day_of_week = Column(Integer)
    start_time = Column(Time)
    end_time = Column(Time)
    created_at = Column(DateTime, default=datetime.utcnow)

    professional = relationship("Professional", back_populates="availability_schedules")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    professional_id = Column(Integer, ForeignKey("professionals.id"))
    appointment_date = Column(DateTime, index=True)
    status = Column(String, default="agendada")
    cancellation_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    professional = relationship("Professional", back_populates="appointments")
    medical_record = relationship("MedicalRecord", back_populates="appointment", uselist=False)
    waiting_list_entry = relationship("WaitingList", back_populates="appointment", uselist=False)

class MedicalRecord(Base):
    __tablename__ = "medical_records"
    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("professionals.id"))
    chief_complaint = Column(Text)
    diagnosis = Column(Text)
    observations = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointment = relationship("Appointment", back_populates="medical_record")
    patient = relationship("Patient", back_populates="medical_records")
    doctor = relationship("Professional", back_populates="medical_records")
    prescriptions = relationship("Prescription", back_populates="medical_record")
    exams = relationship("Exam", back_populates="medical_record")

class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"))
    medication_name = Column(String)
    dosage = Column(String)
    frequency = Column(String)
    duration_days = Column(Integer)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    medical_record = relationship("MedicalRecord", back_populates="prescriptions")

class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"))
    exam_type = Column(String)
    status = Column(String, default="solicitado")
    result = Column(Text, nullable=True)
    result_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    medical_record = relationship("MedicalRecord", back_populates="exams")

class Charge(Base):
    __tablename__ = "charges"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=True)
    amount = Column(Float)
    insurance_discount = Column(Float, default=0)
    payment_method = Column(String, nullable=True)
    status = Column(String, default="pendente")
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="charges")

class WaitingList(Base):
    __tablename__ = "waiting_lists"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True)
    position = Column(Integer)
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointment = relationship("Appointment", back_populates="waiting_list_entry")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String)
    entity_type = Column(String)
    entity_id = Column(Integer)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")
