from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.exceptions import AppError
from app.database import Base, engine
from app.routers import (
    appointments,
    auth,
    billing,
    medical_records,
    patients,
    professionals,
    reports,
    users,
)

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description="API REST para gestão de uma clínica médica de médio porte.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(patients.router)
app.include_router(professionals.router)
app.include_router(appointments.router)
app.include_router(medical_records.router)
app.include_router(billing.router)
app.include_router(reports.router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(loc) for loc in error["loc"][1:]), "message": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Erro de validação nos dados enviados.", "errors": errors},
    )


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.app_name}
