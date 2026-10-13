from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import Base, engine
from app.routers import auth, books, loans, users

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API REST para gerenciamento de biblioteca: usuários, livros e empréstimos.",
    version="1.0.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": exc.errors()}),
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "Database integrity error (possible duplicate or invalid reference)"},
    )


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(books.router)
app.include_router(loans.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}
