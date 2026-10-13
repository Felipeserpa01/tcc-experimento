from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import auth, books, loans

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Gerenciamento de Biblioteca",
    description="Uma API REST completa para gerenciar uma biblioteca",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(loans.router)


@app.get("/")
async def root():
    return {
        "message": "Bem-vindo à API de Gerenciamento de Biblioteca",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
