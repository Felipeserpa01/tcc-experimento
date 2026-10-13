from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routes import auth, books, loans

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Biblioteca API",
    description="API REST para gerenciamento de biblioteca",
    version="1.0.0"
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

@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Bem-vindo à API de Gerenciamento de Biblioteca",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
