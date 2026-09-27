from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff_id: str
    name: str
    role: str


class StaffResponse(BaseModel):
    id: str
    name: str
    username: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True
