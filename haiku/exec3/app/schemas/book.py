from pydantic import BaseModel, Field, ConfigDict

class BookBase(BaseModel):
    title: str
    author: str
    isbn: str
    year: int = Field(..., ge=1000, le=2100)
    total_quantity: int = Field(..., ge=0)
    description: str | None = None

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    year: int | None = None
    total_quantity: int | None = None
    description: str | None = None

class BookResponse(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    available_quantity: int

class BookSearch(BaseModel):
    title: str | None = None
    author: str | None = None
