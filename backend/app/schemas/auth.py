from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    full_name: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role_name: str
    department: str | None = None

    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1)
    password: str = Field(min_length=6)
