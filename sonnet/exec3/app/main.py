from fastapi import FastAPI

from .database import Base, engine
from .routers import auth, books, loans

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Gerenciamento de Biblioteca",
    description=(
        "API REST para gerenciamento de livros, usuários e empréstimos de uma biblioteca."
    ),
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(loans.router)


@app.get("/", tags=["Status"])
def root():
    return {"status": "ok", "message": "API de Gerenciamento de Biblioteca"}


@app.get("/health", tags=["Status"])
def health_check():
    return {"status": "healthy"}
