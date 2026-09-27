"""
Hardware endpoints — authenticated by X-Hardware-Secret header.
Pico W uses these to reserve tokens and check service availability.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.models.schema import IdempotencyRecord, Queue, Service
from app.schemas.token import TokenReservationRequest, TokenReservationResponse
from app.services import queue_manager

router = APIRouter(prefix="/hardware", tags=["hardware"])


def _verify_hardware(x_hardware_secret: str = Header(...)):
    if x_hardware_secret != settings.HARDWARE_SECRET:
        raise HTTPException(status_code=401, detail="Invalid hardware secret")


@router.post(
    "/tokens",
    response_model=TokenReservationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_verify_hardware)],
)
async def reserve_token(
    req: TokenReservationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Pico W reserves a token slot.
    Idempotent: repeated requests with same (device_id, hardware_request_id) return same response.
    """
    # Idempotency check
    idem_res = await db.execute(
        select(IdempotencyRecord).where(
            IdempotencyRecord.device_id == req.device_id,
            IdempotencyRecord.hardware_request_id == req.hardware_request_id,
        )
    )
    existing = idem_res.scalars().first()
    if existing:
        return TokenReservationResponse(**existing.response_payload)

    # Validate service exists
    svc_res = await db.execute(select(Service).where(Service.id == req.service_id))
    if not svc_res.scalars().first():
        raise HTTPException(status_code=404, detail=f"Service {req.service_id} not found")

    try:
        token = await queue_manager.reserve_token(
            db,
            service_id=req.service_id,
            hardware_reservation_id=req.hardware_reservation_id,
            display_number=req.display_number,
            claim_secret_hash=req.claim_secret_hash,
            device_id=req.device_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    response_data = {
        "token_id": token.id,
        "display_number": token.display_number,
        "reservation_expires_at": token.reservation_expires_at.isoformat(),
        "acknowledged": True,
    }

    # Store idempotency record in same transaction
    db.add(IdempotencyRecord(
        device_id=req.device_id,
        hardware_request_id=req.hardware_request_id,
        response_payload=response_data,
    ))

    await db.commit()
    await db.refresh(token)

    return TokenReservationResponse(**response_data)


@router.get("/services", tags=["hardware"], dependencies=[Depends(_verify_hardware)])
async def list_services(db: AsyncSession = Depends(get_db)):
    """Pico W queries available services."""
    result = await db.execute(select(Service))
    services = result.scalars().all()
    return [{"id": s.id, "name": s.name} for s in services]
