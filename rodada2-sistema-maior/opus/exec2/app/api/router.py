from fastapi import APIRouter

from app.api.routes import (
    appointments,
    audit,
    auth,
    billing,
    exams,
    insurances,
    notifications,
    patients,
    professionals,
    reports,
    users,
    waitlist,
)

api_router = APIRouter()
for module in (
    auth,
    users,
    insurances,
    patients,
    professionals,
    appointments,
    waitlist,
    exams,
    billing,
    reports,
    audit,
    notifications,
):
    api_router.include_router(module.router)
