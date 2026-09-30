from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class TokenReservationRequest(BaseModel):
    """Sent by Pico W to reserve a token."""
    device_id: str
    hardware_request_id: str          # Unique ID per physical button press
    hardware_reservation_id: str      # Pico-generated token reservation ID
    service_id: str
    display_number: str               # Pico-generated display number (e.g. "A-024")
    claim_secret_hash: str            # SHA-256 of claim_secret encoded in QR
    category: Optional[str] = None    # Explicit customer category; legacy callers may omit


class TokenReservationResponse(BaseModel):
    token_id: str
    display_number: str
    reservation_expires_at: datetime
    acknowledged: bool = True
    customer_entry_path: Optional[str] = None


class ClaimRequest(BaseModel):
    """Browser claims a token after scanning QR."""
    hardware_reservation_id: str
    claim_secret_hash: str
    recovery_credential_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    browser_session_id: str = Field(min_length=16, max_length=128)
    service_id: Optional[str] = None
    display_number: Optional[str] = None


class ClaimResponse(BaseModel):
    token_id: str
    display_number: str
    status: str
    queue_id: str
    reservation_expires_at: datetime
    claim_session_id: str
    scan_sequence: Optional[int] = None
    service_id: str
    registered_at: Optional[datetime] = None
    server_time: datetime


class RecoveryRequest(BaseModel):
    token_id: str
    claim_session_id: str = Field(min_length=16, max_length=128)
    recovery_credential_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class RegistrationRequest(RecoveryRequest):
    """Browser submits form to activate the token."""
    tracking_secret_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    customer_name: str = Field(min_length=2, max_length=120)
    phone_number: str = Field(pattern=r"^[6-9][0-9]{9}$")
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)

    @field_validator("customer_name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class RegistrationResponse(BaseModel):
    token_id: str
    display_number: str
    status: str
    scan_sequence: int
    queue_position: Optional[int] = None


class TokenStatusResponse(BaseModel):
    token_id: str
    display_number: str
    status: str
    scan_sequence: Optional[int] = None
    sort_key: Optional[int] = None
    recall_attempts: int
    called_at: Optional[datetime] = None
    serving_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    people_ahead: Optional[int] = None
    estimated_wait_minutes: Optional[int] = None
    counter_label: Optional[str] = None
    server_time: datetime

    class Config:
        from_attributes = True
