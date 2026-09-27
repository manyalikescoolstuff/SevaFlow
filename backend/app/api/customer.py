"""
Customer-facing endpoints: QR scan claim and form registration.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.token import (
    ClaimRequest, ClaimResponse,
    RegistrationRequest, RegistrationResponse,
    TokenStatusResponse,
)
from app.models.schema import Token
from app.services import queue_manager
from sqlalchemy import select, func

router = APIRouter(prefix="/customer", tags=["customer"])


@router.post("/claim", response_model=ClaimResponse)
async def claim_token(req: ClaimRequest, db: AsyncSession = Depends(get_db)):
    """
    Browser claims a token after scanning the QR code.
    Browser must generate recovery_credential and browser_session_id BEFORE calling this.
    """
    try:
        token = await queue_manager.claim_token(
            db,
            hardware_reservation_id=req.hardware_reservation_id,
            claim_secret_hash=req.claim_secret_hash,
            recovery_credential_hash=req.recovery_credential_hash,
            browser_session_id=req.browser_session_id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await db.commit()
    await db.refresh(token)

    return ClaimResponse(
        token_id=token.id,
        display_number=token.display_number,
        status=token.status,
        queue_id=token.queue_id,
        reservation_expires_at=token.reservation_expires_at,
    )


@router.post("/register", response_model=RegistrationResponse)
async def register_token(req: RegistrationRequest, db: AsyncSession = Depends(get_db)):
    """
    Customer completes registration form, activating the token in the queue.
    """
    try:
        token = await queue_manager.register_token(
            db,
            token_id=req.token_id,
            claim_session_id=req.claim_session_id,
            tracking_secret_hash=req.tracking_secret_hash,
            customer_name=req.customer_name,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await db.commit()
    await db.refresh(token)

    # Calculate approximate queue position
    pos_res = await db.execute(
        select(func.count()).where(
            Token.queue_id == token.queue_id,
            Token.status == "WAITING",
            Token.sort_key < token.sort_key,
        )
    )
    position = (pos_res.scalar() or 0) + 1

    return RegistrationResponse(
        token_id=token.id,
        display_number=token.display_number,
        status=token.status,
        scan_sequence=token.scan_sequence,
        queue_position=position,
    )


@router.get("/token/{token_id}/status", response_model=TokenStatusResponse)
async def get_token_status(token_id: str, db: AsyncSession = Depends(get_db)):
    """Customer polling endpoint for their token status."""
    result = await db.execute(select(Token).where(Token.id == token_id))
    token = result.scalars().first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    return TokenStatusResponse(
        token_id=token.id,
        display_number=token.display_number,
        status=token.status,
        scan_sequence=token.scan_sequence,
        sort_key=token.sort_key,
        recall_attempts=token.recall_attempts,
        called_at=token.called_at,
        serving_started_at=token.serving_started_at,
        completed_at=token.completed_at,
    )
