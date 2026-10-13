from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.database import Base, engine
from app.routers import auth, books, loans

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Library Management API",
    description="API REST para gerenciamento de biblioteca: usuários, livros e empréstimos.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(loans.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc: SQLAlchemyError):
    return JSONResponse(status_code=500, content={"detail": "Database error"})


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok"}
