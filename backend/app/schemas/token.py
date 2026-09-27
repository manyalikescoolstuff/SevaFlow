from pydantic import BaseModel
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


class TokenReservationResponse(BaseModel):
    token_id: str
    display_number: str
    reservation_expires_at: datetime
    acknowledged: bool = True


class ClaimRequest(BaseModel):
    """Browser claims a token after scanning QR."""
    hardware_reservation_id: str
    claim_secret_hash: str
    recovery_credential_hash: str     # Browser-generated before this request
    browser_session_id: str           # Browser-generated session ID


class ClaimResponse(BaseModel):
    token_id: str
    display_number: str
    status: str
    queue_id: str
    reservation_expires_at: datetime


class RegistrationRequest(BaseModel):
    """Browser submits form to activate the token."""
    token_id: str
    claim_session_id: str
    tracking_secret_hash: str
    customer_name: str
    phone_number: Optional[str] = None


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

    class Config:
        from_attributes = True
