from pydantic import BaseModel
from typing import List

class QueueBase(BaseModel):
    service_id: str
    recent_history: List[int] = []

class QueueCreate(QueueBase):
    id: str

class Queue(QueueBase):
    id: str

    class Config:
        from_attributes = True
