from pydantic import BaseModel
from typing import Optional

class ServiceBase(BaseModel):
    name: str
    expected_duration_sec: int

class ServiceCreate(ServiceBase):
    id: str

class Service(ServiceBase):
    id: str

    class Config:
        from_attributes = True
