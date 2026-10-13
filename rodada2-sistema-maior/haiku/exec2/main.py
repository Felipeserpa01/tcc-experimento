from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.routes import auth, patients, professionals, appointments, records, billing, reports

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Clinic Management API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(professionals.router, prefix="/api/professionals", tags=["Professionals"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["Appointments"])
app.include_router(records.router, prefix="/api/records", tags=["Medical Records"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
