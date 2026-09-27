from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CounterBase(BaseModel):
    label: str
    service_id: str
    queue_id: str
    status: str
    staff_id: Optional[str] = None
    current_token_id: Optional[str] = None
    served_today: int = 0
    avg_service_time_sec: int = 0
    serving_started_at: Optional[datetime] = None
    utilization_rate: Optional[int] = 0

class CounterCreate(CounterBase):
    id: str

class Counter(CounterBase):
    id: str

    class Config:
        from_attributes = True
