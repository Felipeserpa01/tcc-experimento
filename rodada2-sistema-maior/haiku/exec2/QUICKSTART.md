# Quick Start Guide

## Installation (5 minutes)

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
uvicorn main:app --reload
```

Server runs at: `http://localhost:8000`

## Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## First Steps - Test the API

### 1. Register a User
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@clinic.com",
    "username": "doctor1",
    "full_name": "Dr. John Smith",
    "role": "doctor",
    "password": "SecurePass123!"
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "doctor1",
    "password": "SecurePass123!"
  }'
```

Copy the `access_token` from the response.

### 3. Use the Token
```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage
pytest --cov=app

# Run specific test
pytest tests/test_auth.py::test_user_registration -v
```

## Key Workflows

### Create a Medical Workflow

1. **Register Patient**
```bash
POST /api/patients/
{
  "user_id": 1,
  "cpf": "12345678901",
  "date_of_birth": "1990-01-15",
  "sex": "M",
  "phone": "11999999999",
  "address": "Rua Test, 123",
  "city": "São Paulo",
  "state": "SP",
  "zip_code": "01234-567",
  "insurance_plan": "Unimed",
  "allergies": "Penicilina"
}
```

2. **Create Appointment**
```bash
POST /api/appointments/
{
  "patient_id": 1,
  "professional_id": 2,
  "appointment_date": "2024-02-15T10:00:00"
}
```

3. **Confirm Appointment**
```bash
POST /api/appointments/1/confirm
```

4. **Create Medical Record**
```bash
POST /api/records/
{
  "appointment_id": 1,
  "patient_id": 1,
  "doctor_id": 2,
  "chief_complaint": "Fever and cough",
  "diagnosis": "Common cold"
}
```

5. **Add Prescription**
```bash
POST /api/records/1/prescriptions
{
  "medical_record_id": 1,
  "medication_name": "Paracetamol",
  "dosage": "500mg",
  "frequency": "Every 8 hours",
  "duration_days": 7
}
```

6. **Create Charge**
```bash
POST /api/billing/charges
{
  "patient_id": 1,
  "appointment_id": 1,
  "amount": 150.00,
  "status": "pendente"
}
```

7. **Record Payment**
```bash
POST /api/billing/charges/1/pay?payment_method=credit_card
```

## API Response Examples

### Success Response (200)
```json
{
  "id": 1,
  "email": "patient@example.com",
  "username": "patient1",
  "full_name": "John Patient",
  "role": "patient",
  "is_active": true,
  "created_at": "2024-02-01T10:00:00"
}
```

### Error Response (400)
```json
{
  "detail": "Invalid CPF"
}
```

### Error Response (401)
```json
{
  "detail": "Invalid credentials"
}
```

### Error Response (403)
```json
{
  "detail": "Insufficient permissions"
}
```

## Database

The SQLite database file (`clinic.db`) is created automatically on first run. It contains all tables and relationships.

To reset database:
```bash
rm clinic.db
```

## Environment Variables

Edit `.env` file:
```
DATABASE_URL=sqlite:///clinic.db
SECRET_KEY=your-secret-key
```

## Project Structure Quick Reference

```
haiku/exec2/
├── main.py                    # Application entry
├── requirements.txt           # Dependencies
├── .env.example              # Environment template
├── README.md                 # Full documentation
├── IMPLEMENTATION_SUMMARY.md # What was built
├── QUICKSTART.md            # This file
├── app/
│   ├── models.py            # Database models
│   ├── schemas.py           # Request/response validation
│   ├── database.py          # DB configuration
│   ├── security.py          # Auth & hashing
│   ├── services/            # Business logic (7 files)
│   ├── repositories/        # Data access (10 files)
│   └── routes/              # API endpoints (7 files)
└── tests/                   # Test suite (4+ files)
```

## Troubleshooting

### Port Already in Use
```bash
uvicorn main:app --reload --port 8001
```

### Database Locked
```bash
rm clinic.db
rm test.db
```

### Module Not Found
```bash
pip install -r requirements.txt --upgrade
```

### Token Invalid
- Make sure you're including `Authorization: Bearer <token>` header
- Token might be expired (access tokens expire in 15 minutes)
- Use refresh endpoint to get new access token

## Next Steps

1. Read `README.md` for comprehensive API documentation
2. Check `IMPLEMENTATION_SUMMARY.md` for architecture details
3. Explore `tests/` folder to understand usage patterns
4. Use Swagger UI (`/docs`) to test endpoints interactively
5. Deploy to production following guidelines in README

## Support

For issues or questions:
1. Check API documentation in Swagger UI
2. Review README.md for detailed endpoint specs
3. Look at test files for usage examples
4. Check IMPLEMENTATION_SUMMARY.md for architecture details

---

**Happy testing! 🚀**
