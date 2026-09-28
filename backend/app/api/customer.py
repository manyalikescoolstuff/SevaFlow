"""Customer claim, authenticated recovery, registration and tracking."""
import math
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.schema import Token, Queue, Counter, Service
from app.schemas.token import (
    ClaimRequest, ClaimResponse, RecoveryRequest,
    RegistrationRequest, RegistrationResponse, TokenStatusResponse,
)
from app.services import queue_manager as qm


def no_store(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/customer", tags=["customer"], dependencies=[Depends(no_store)])


async def mutate(db, operation, **kwargs):
    try:
        token = await operation(db, **kwargs)
        await db.commit()
        await db.refresh(token)
        return token
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except qm.ReservationExpired as exc:
        raise HTTPException(410, str(exc)) from exc
    except qm.CustomerConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


async def claim_response(db, token):
    service_id = (await db.execute(select(Queue.service_id).where(Queue.id == token.queue_id))).scalar_one()
    return ClaimResponse(
        token_id=token.id, display_number=token.display_number, status=token.status,
        queue_id=token.queue_id, service_id=service_id,
        claim_session_id=token.claim_session_id, scan_sequence=token.scan_sequence,
        reservation_expires_at=token.reservation_expires_at,
        registered_at=token.registered_at, server_time=qm._now(),
    )


@router.post("/claim", response_model=ClaimResponse)
async def claim_token(req: ClaimRequest, db: AsyncSession = Depends(get_db)):
    token = await mutate(db, qm.claim_token, **req.model_dump())
    return await claim_response(db, token)


@router.post("/recover", response_model=ClaimResponse)
async def recover_token(req: RecoveryRequest, db: AsyncSession = Depends(get_db)):
    token = await mutate(db, qm.recover_token, **req.model_dump())
    return await claim_response(db, token)


@router.post("/reject", response_model=ClaimResponse)
async def reject_token(req: RecoveryRequest, db: AsyncSession = Depends(get_db)):
    token = await mutate(db, qm.reject_token, **req.model_dump())
    return await claim_response(db, token)


@router.post("/register", response_model=RegistrationResponse)
async def register_token(req: RegistrationRequest, db: AsyncSession = Depends(get_db)):
    token = await mutate(db, qm.register_token, **req.model_dump())
    position = None
    if token.status == "WAITING":
        count = (await db.execute(select(func.count()).select_from(Token).where(
            Token.queue_id == token.queue_id, Token.status == "WAITING",
            Token.sort_key < token.sort_key,
        ))).scalar_one()
        position = count + 1
    return RegistrationResponse(token_id=token.id, display_number=token.display_number,
                                status=token.status, scan_sequence=token.scan_sequence,
                                queue_position=position)


@router.get("/token/{token_id}/status", response_model=TokenStatusResponse)
async def get_token_status(token_id: str, x_tracking_secret: str = Header(...),
                           db: AsyncSession = Depends(get_db)):
    token = (await db.execute(select(Token).where(Token.id == token_id))).scalar_one_or_none()
    if not token or not qm._matches(token.tracking_secret_hash, x_tracking_secret):
        raise HTTPException(403, "Invalid tracking credential")
    counters = (await db.execute(select(Counter).where(Counter.queue_id == token.queue_id))).scalars().all()
    assigned = next((c for c in counters if c.current_token_id == token.id), None)
    ahead = estimate = None
    if token.status == "WAITING":
        waiting_ahead = (await db.execute(select(func.count()).select_from(Token).where(
            Token.queue_id == token.queue_id, Token.status == "WAITING",
            Token.sort_key < token.sort_key,
        ))).scalar_one()
        ahead = waiting_ahead + sum(c.current_token_id is not None for c in counters)
        active = [c for c in counters if c.status == "ACTIVE"]
        if active:
            default = (await db.execute(select(Service.expected_duration_sec)
                .join(Queue, Queue.service_id == Service.id).where(Queue.id == token.queue_id))).scalar_one()
            # Approximation; recalls and service-duration changes can alter this wait.
            average = sum(c.avg_service_time_sec or default for c in active) / len(active)
            estimate = math.ceil(ahead * average / len(active) / 60)
    return TokenStatusResponse(
        token_id=token.id, display_number=token.display_number, status=token.status,
        scan_sequence=token.scan_sequence, sort_key=token.sort_key,
        recall_attempts=token.recall_attempts, called_at=token.called_at,
        serving_started_at=token.serving_started_at, completed_at=token.completed_at,
        people_ahead=ahead, estimated_wait_minutes=estimate,
        counter_label=assigned.label if assigned else None, server_time=qm._now(),
    )
