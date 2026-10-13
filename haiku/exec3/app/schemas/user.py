from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.user import UserType

class UserBase(BaseModel):
    username: str
    email: EmailStr
    user_type: UserType = UserType.READER

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
