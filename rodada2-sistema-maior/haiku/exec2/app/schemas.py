from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime, date, time
from typing import Optional, List
from app.models import UserRole

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str
    role: UserRole

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @validator('password')
    def validate_password(cls, v):
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        if not (has_letter and has_digit and has_special):
            raise ValueError("Password must contain letters, digits and special characters")
        return v

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class PatientBase(BaseModel):
    cpf: str = Field(..., regex=r"^\d{11}$")
    date_of_birth: date
    sex: str
    phone: str
    address: str
    city: str
    state: str
    zip_code: str
    insurance_plan: Optional[str] = None
    allergies: Optional[str] = None
    observations: Optional[str] = None

class PatientCreate(PatientBase):
    user_id: int

class PatientUpdate(BaseModel):
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    insurance_plan: Optional[str] = None
    allergies: Optional[str] = None
    observations: Optional[str] = None

class PatientResponse(PatientBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ProfessionalBase(BaseModel):
    registration_number: str = Field(..., regex=r"^\d{5,10}$")
    specialization: str
    phone: Optional[str] = None

class ProfessionalCreate(ProfessionalBase):
    user_id: int

class ProfessionalResponse(ProfessionalBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class AvailabilityScheduleBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: time
    end_time: time

class AvailabilityScheduleCreate(AvailabilityScheduleBase):
    professional_id: int

class AvailabilityScheduleResponse(AvailabilityScheduleBase):
    id: int
    professional_id: int

    class Config:
        from_attributes = True

class AppointmentBase(BaseModel):
    patient_id: int
    professional_id: int
    appointment_date: datetime

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    cancellation_reason: Optional[str] = None
    notes: Optional[str] = None

class AppointmentResponse(AppointmentBase):
    id: int
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PrescriptionBase(BaseModel):
    medication_name: str
    dosage: str
    frequency: str
    duration_days: int
    notes: Optional[str] = None

class PrescriptionCreate(PrescriptionBase):
    medical_record_id: int

class PrescriptionResponse(PrescriptionBase):
    id: int
    medical_record_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ExamBase(BaseModel):
    exam_type: str
    status: str = "solicitado"
    result: Optional[str] = None
    result_url: Optional[str] = None

class ExamCreate(ExamBase):
    medical_record_id: int

class ExamUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None
    result_url: Optional[str] = None

class ExamResponse(ExamBase):
    id: int
    medical_record_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MedicalRecordBase(BaseModel):
    chief_complaint: str
    diagnosis: str
    observations: Optional[str] = None

class MedicalRecordCreate(MedicalRecordBase):
    appointment_id: int
    patient_id: int
    doctor_id: int

class MedicalRecordResponse(MedicalRecordBase):
    id: int
    appointment_id: int
    patient_id: int
    doctor_id: int
    prescriptions: List[PrescriptionResponse] = []
    exams: List[ExamResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

class ChargeBase(BaseModel):
    amount: float = Field(..., gt=0)
    insurance_discount: float = Field(default=0, ge=0)
    payment_method: Optional[str] = None
    status: str = "pendente"

class ChargeCreate(ChargeBase):
    patient_id: int
    appointment_id: Optional[int] = None
    exam_id: Optional[int] = None

class ChargeUpdate(BaseModel):
    status: str
    payment_method: Optional[str] = None

class ChargeResponse(ChargeBase):
    id: int
    patient_id: int
    appointment_id: Optional[int]
    exam_id: Optional[int]
    paid_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class WaitingListResponse(BaseModel):
    id: int
    patient_id: int
    appointment_id: int
    position: int
    notified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)

    @validator('new_password')
    def validate_password(cls, v):
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        if not (has_letter and has_digit and has_special):
            raise ValueError("Password must contain letters, digits and special characters")
        return v

class PasswordResetRequest(BaseModel):
    email: EmailStr

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    entity_type: str
    entity_id: int
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str
