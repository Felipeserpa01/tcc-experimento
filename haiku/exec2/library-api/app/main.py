from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routes import auth_router, books_router, loans_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Library API",
    description="A complete REST API for library management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(books_router)
app.include_router(loans_router)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to Library API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
