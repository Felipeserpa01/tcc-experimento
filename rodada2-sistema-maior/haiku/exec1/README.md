# Medical Clinic Management API

A production-ready REST API for managing a mid-size medical clinic, built with FastAPI, SQLAlchemy, and SQLite.

## Features

- **Authentication & Authorization**
  - JWT-based authentication with access and refresh tokens
  - 5 role-based access control: Admin, Doctor, Nurse, Receptionist, Patient
  - Account lockout after 5 failed login attempts
  - Password reset and change endpoints

- **Patient Management**
  - Complete CRUD operations
  - CPF validation and uniqueness enforcement
  - Insurance plan tracking
  - Clinical history view

- **Professional Management**
  - Unified doctor/nurse profile management
  - CRM/license validation
  - Weekly availability scheduling
  - Specialty tracking

- **Appointment Scheduling**
  - Double-booking prevention with DB constraints
  - Availability window validation
  - Status tracking (scheduled, confirmed, in_progress, completed, cancelled, no_show)
  - Waitlist management with automatic notification

- **Clinical Records**
  - Medical record entries per appointment
  - Prescription management
  - Exam requests with result tracking
  - Doctor-only write access, patient read-only access

- **Billing & Financial**
  - Charge and payment tracking
  - Insurance discount application
  - Multiple payment method support
  - Revenue reporting by period and method

- **Audit & Compliance**
  - Complete audit trail of sensitive actions
  - User activity logging
  - Forensic data retrieval

- **Reporting**
  - Appointments report by period, doctor, specialty
  - No-show rate tracking by doctor
  - Revenue analysis
  - Most-seen patients report

## Installation

### Prerequisites
- Python 3.9+
- pip

### Setup

1. Clone the repository:
```bash
cd /Users/felipeserpa/Desktop/tcc-experimento/rodada2-sistema-maior/haiku/exec1
```

2. Create a virtual environment (optional but recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

5. (Optional) Run Alembic migrations:
```bash
alembic upgrade head
```

6. Seed initial admin user:
```bash
python3 scripts/seed_admin.py
```

## Running the Application

### Development server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Check health
```bash
curl http://localhost:8000/health
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

### Run all tests
```bash
pytest
```

### Run only unit tests
```bash
pytest tests/unit/
```

### Run only integration tests
```bash
pytest tests/integration/
```

### With coverage report
```bash
pytest --cov=app tests/
```

## Project Structure

```
app/
├── api/v1/              # API route handlers
│   ├── auth.py          # Authentication endpoints
│   ├── patients.py      # Patient CRUD
│   ├── professionals.py # Doctor/nurse management
│   ├── appointments.py  # Scheduling
│   ├── medical_records.py
│   ├── prescriptions.py
│   ├── exams.py
│   ├── billing.py       # Charges and payments
│   └── reports.py       # Analytics
├── core/                # Core utilities
│   ├── config.py        # Settings and env vars
│   ├── security.py      # JWT and password hashing
│   ├── exceptions.py    # Custom exceptions
│   ├── enums.py         # Enum definitions
│   └── dependencies.py  # FastAPI dependencies
├── db/                  # Database setup
│   ├── base.py          # ORM base and metadata
│   └── session.py       # Database connection
├── models/              # SQLAlchemy ORM models
├── repositories/        # Data access layer
├── services/            # Business logic layer
├── schemas/             # Pydantic request/response models
└── utils/               # Validation and utility functions

tests/
├── unit/                # Unit tests
├── integration/         # Integration tests
└── conftest.py          # Pytest fixtures
```

## Authentication Flow

1. **Register** - Create a new patient account:
```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "patient@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

2. **Login** - Get access and refresh tokens:
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "patient@example.com",
  "password": "SecurePass123!"
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user_id": 1,
  "role": "patient"
}
```

3. **Use Token** - Include in Authorization header:
```bash
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

4. **Refresh Token** - Get new tokens:
```bash
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "<refresh_token>"
}
```

## Key Business Rules

### Appointments
- Double-booking is prevented at both service and database level
- Cannot schedule outside doctor's availability window
- Cannot schedule in the past
- Supports 6 statuses: scheduled, confirmed, in_progress, completed, cancelled, no_show

### Clinical Records
- Only the assigned doctor can create/edit medical records and prescriptions
- Patients can view but not edit their own records
- Exams are tracked with status: requested, completed

### Billing
- Charges can be linked to appointments or exams
- Insurance discount automatically applied if patient has insurance plan
- Prevents double payment of same charge
- Supports 5 payment methods: cash, credit_card, debit_card, pix, insurance

### Security
- Passwords require: min 8 chars, letters, numbers, symbols
- Account locked for 30 minutes after 5 failed login attempts
- Refresh tokens are hashed and can be revoked
- All sensitive actions logged to audit trail

## Environment Variables

See `.env.example` for all available settings. Key ones:

```
DATABASE_URL=sqlite:///./clinic.db
SECRET_KEY=<your-secret-key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30
INSURANCE_DEFAULT_DISCOUNT_PERCENT=10
DEBUG=False
```

## Database Schema

14 tables:
- `users` - Authentication and role management
- `patients` - Patient demographics
- `professionals` - Doctor/nurse profiles
- `availability_slots` - Weekly schedule per professional
- `appointments` - Scheduled consultations
- `waitlist_entries` - Overflow queue management
- `medical_records` - Clinical notes per appointment
- `prescriptions` - Medications prescribed
- `exams` - Diagnostic tests
- `charges` - Billable items
- `payments` - Payment records
- `audit_logs` - Action audit trail
- `refresh_tokens` - Token management
- `password_reset_tokens` - Password reset flow

## Performance Considerations

- SQLite is suitable for development and small deployments
- For production with concurrent load, migrate to PostgreSQL
- Indexes on frequently queried columns (email, CPF, appointment date)
- Pagination defaults to 20 items per page, max 100

## Deployment Notes

**Before going to production:**
1. Change `SECRET_KEY` to a strong random value
2. Set `DEBUG=False`
3. Configure `ALLOWED_ORIGINS` for CORS
4. Remove the demo password reset token from response body (line in auth.py)
5. Migrate to PostgreSQL for production database
6. Set up proper email service for password resets
7. Enable HTTPS
8. Configure rate limiting
9. Set up proper logging infrastructure

## License

Internal use for TCC experiment - Haiku execution round 2
