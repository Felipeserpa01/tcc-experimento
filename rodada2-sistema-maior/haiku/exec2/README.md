# Clinic Management API

A comprehensive, production-ready medical clinic management REST API built with FastAPI, featuring authentication, appointment scheduling, medical records, billing, and advanced reporting capabilities.

## 🏗️ Architecture

The system follows a layered architecture pattern:
- **Routes Layer**: FastAPI endpoints with request validation and access control
- **Service Layer**: Business logic and complex workflows
- **Repository Layer**: Database access and ORM operations
- **Model Layer**: SQLAlchemy ORM models and data structures
- **Schema Layer**: Pydantic models for validation

## 📦 Key Features

### 1. Authentication & Security
- JWT-based authentication with access and refresh tokens
- Five role-based profiles: Admin, Doctor, Nurse, Receptionist, Patient
- Granular access control on all endpoints
- Password hashing with bcrypt
- Account lockout after 5 failed login attempts
- Password policy enforcement (8+ chars, letters, numbers, symbols)
- Audit logging for sensitive actions

### 2. Patient Management
- Complete CRUD operations for patient records
- CPF validation with checksum verification
- Insurance plan tracking
- Allergy and medical history notes
- Full-text search with pagination
- Role-based access control (patients see only own data)

### 3. Professional Management
- Doctor and nurse registration with credentials
- CRM validation
- Specialization tracking
- Availability schedule management
- Day-of-week and time slot configuration

### 4. Appointment Scheduling
- Intelligent conflict detection and prevention
- Availability checking against professional schedules
- Automated waiting list management
- Status tracking (agendada, confirmada, em andamento, realizada, cancelada, faltou)
- Appointment rescheduling and cancellation with reasons
- Doctor daily agenda retrieval

### 5. Medical Records & Prescriptions
- Consultation documentation (chief complaint, diagnosis, observations)
- Prescription management (medication, dosage, frequency, duration)
- Exam ordering and result tracking
- Complete patient medical history
- Access control (patients view own, doctors manage their consultations)

### 6. Billing & Payments
- Charge creation and management
- Automatic insurance discount calculation (10% for insured patients)
- Multiple payment methods support
- Payment status tracking (pendente, pago, cancelado)
- Prevention of duplicate payments
- Financial reports by period and payment method

### 7. Reports & Analytics
- Appointments by period, doctor, and specialization
- Revenue analysis by period and payment method
- No-show rate per doctor
- Most frequently attended patients
- Complete audit trail of system actions

## 🛠️ Technology Stack

- **Framework**: FastAPI 0.104.1
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: JWT with Python-Jose
- **Password Security**: Passlib with Bcrypt
- **API Documentation**: Automatic Swagger UI and ReDoc
- **Testing**: Pytest with fixtures
- **Server**: Uvicorn

## 📋 Installation & Setup

### Prerequisites
- Python 3.9+
- pip or Poetry

### Steps

1. **Clone and navigate to project**
```bash
cd haiku/exec2
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Run the application**
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

API Documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🧪 Testing

Run all tests:
```bash
pytest
```

Run specific test file:
```bash
pytest tests/test_auth.py -v
```

Run with coverage:
```bash
pytest --cov=app tests/
```

## 📚 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/change-password` - Change user password
- `GET /api/auth/me` - Get current user info

### Patients
- `POST /api/patients/` - Create patient
- `GET /api/patients/` - List patients (with search/filter)
- `GET /api/patients/{patient_id}` - Get patient details
- `PUT /api/patients/{patient_id}` - Update patient
- `DELETE /api/patients/{patient_id}` - Delete patient

### Professionals
- `POST /api/professionals/` - Register professional
- `GET /api/professionals/` - List professionals (by specialization)
- `GET /api/professionals/{professional_id}` - Get professional
- `POST /api/professionals/{professional_id}/availability` - Add availability slot
- `GET /api/professionals/{professional_id}/availability` - Get availability

### Appointments
- `POST /api/appointments/` - Create appointment (or add to waiting list)
- `GET /api/appointments/{appointment_id}` - Get appointment
- `PUT /api/appointments/{appointment_id}` - Update appointment
- `POST /api/appointments/{appointment_id}/confirm` - Confirm appointment
- `POST /api/appointments/{appointment_id}/cancel` - Cancel appointment
- `POST /api/appointments/{appointment_id}/reschedule` - Reschedule appointment
- `GET /api/appointments/professional/{professional_id}/agenda` - Doctor's daily agenda
- `GET /api/appointments/patient/{patient_id}/appointments` - Patient's appointments

### Medical Records
- `POST /api/records/` - Create medical record
- `GET /api/records/{record_id}` - Get record
- `GET /api/records/patient/{patient_id}/history` - Get patient's full history
- `POST /api/records/{record_id}/prescriptions` - Add prescription
- `GET /api/records/{record_id}/prescriptions` - Get prescriptions
- `POST /api/records/{record_id}/exams` - Order exam
- `PUT /api/records/exams/{exam_id}/result` - Update exam results
- `GET /api/records/{record_id}/exams` - Get exam results

### Billing
- `POST /api/billing/charges` - Create charge
- `GET /api/billing/charges/{charge_id}` - Get charge
- `POST /api/billing/charges/{charge_id}/pay` - Record payment
- `POST /api/billing/charges/{charge_id}/cancel` - Cancel charge
- `GET /api/billing/patient/{patient_id}/charges` - List patient charges
- `GET /api/billing/patient/{patient_id}/charges/unpaid` - Get unpaid charges

### Reports
- `GET /api/reports/appointments/period` - Appointments by date range
- `GET /api/reports/appointments/doctor/{professional_id}` - Doctor's appointments
- `GET /api/reports/appointments/specialization/{specialization}` - By specialty
- `GET /api/reports/appointments/count-by-status` - Status distribution
- `GET /api/reports/revenue/period` - Revenue by period
- `GET /api/reports/revenue/payment-method` - Revenue by payment method
- `GET /api/reports/no-show-rate` - No-show statistics
- `GET /api/reports/most-attended-patients` - Top patients
- `GET /api/reports/audit-logs` - Audit trail

## 🔐 Access Control

### Permissions by Role

**Admin**: Full system access
- Create/delete users and professionals
- Manage all patients and records
- View all reports and audit logs

**Doctor**: Medical operations
- View/create medical records and prescriptions
- Order and update exam results
- View own appointments
- Create availability schedules

**Nurse**: Clinical support
- View patient records and medical history
- Support doctors with exams
- Confirm appointments

**Receptionist**: Administrative
- Manage patient records
- Create/reschedule appointments
- Handle billing and payments
- View reports

**Patient**: Self-service
- View own profile and medical records
- Schedule appointments
- View prescriptions and exams
- Pay bills

## 📊 Business Rules Enforced

1. **Appointments**: Cannot be scheduled outside professional availability or in the past
2. **Conflicts**: Automatic waiting list creation when slots are full
3. **CPF**: Validated with checksum algorithm; duplicate prevention
4. **Billing**: Automatic 10% discount for insured patients; prevents duplicate payments
5. **Access**: Patients only access own data; strict role-based controls
6. **Passwords**: Enforced complexity with 8+ chars, letters, numbers, symbols
7. **Account Security**: 5-attempt lockout for 15 minutes
8. **Audit Trail**: All sensitive actions logged with user and timestamp

## 📁 Project Structure

```
├── main.py                      # Application entry point
├── requirements.txt             # Dependencies
├── app/
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic validation schemas
│   ├── database.py             # Database configuration
│   ├── security.py             # Authentication and hashing
│   ├── utils.py                # Utility functions
│   ├── dependencies.py         # FastAPI dependencies
│   ├── services/               # Business logic layer
│   │   ├── auth_service.py
│   │   ├── patient_service.py
│   │   ├── professional_service.py
│   │   ├── appointment_service.py
│   │   ├── medical_record_service.py
│   │   ├── billing_service.py
│   │   └── reports_service.py
│   ├── repositories/           # Data access layer
│   │   ├── user_repository.py
│   │   ├── patient_repository.py
│   │   ├── professional_repository.py
│   │   ├── appointment_repository.py
│   │   ├── medical_record_repository.py
│   │   ├── exam_repository.py
│   │   ├── prescription_repository.py
│   │   ├── charge_repository.py
│   │   ├── waiting_list_repository.py
│   │   └── availability_schedule_repository.py
│   └── routes/                 # API endpoints
│       ├── auth.py
│       ├── patients.py
│       ├── professionals.py
│       ├── appointments.py
│       ├── records.py
│       ├── billing.py
│       └── reports.py
└── tests/                      # Test suite
    ├── test_auth.py
    ├── test_appointments.py
    ├── test_billing.py
    ├── test_patients.py
    └── conftest.py
```

## 🚀 Production Considerations

1. **Database**: Change from SQLite to PostgreSQL/MySQL
2. **Secrets**: Use environment variables or secret management
3. **HTTPS**: Enable SSL/TLS in production
4. **Rate Limiting**: Add rate limiting middleware
5. **Caching**: Implement Redis for frequent queries
6. **Logging**: Configure centralized logging
7. **Monitoring**: Add health checks and metrics
8. **Backup**: Implement database backup strategy

## 📝 License

This project is part of academic research.

## 👥 Contributors

Generated with Claude Haiku 4.5
