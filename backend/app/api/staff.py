"""
Staff endpoints: login, counter operations (Call Next, Start Service, Missed, Absent Again).
All mutating actions require a valid staff JWT.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_staff, get_counter_staff
from app.core.security import verify_password, create_access_token
from app.models.schema import Counter, Staff, Token, Queue, Service
from app.schemas.counter import Counter as CounterSchema
from app.schemas.staff import LoginRequest, LoginResponse, StaffResponse
from app.services import queue_manager
from app.api.workstation import CommandRequest, command as workstation_command

router = APIRouter(tags=["staff"])


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@router.post("/auth/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Staff).where(Staff.username == form_data.username))
    staff = result.scalars().first()
    if not staff or not verify_password(form_data.password, staff.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not staff.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token({"sub": staff.id, "role": staff.role})
    return LoginResponse(
        access_token=token,
        staff_id=staff.id,
        name=staff.name,
        role=staff.role,
    )


@router.get("/auth/me", response_model=StaffResponse)
async def get_me(current_staff: Staff = Depends(get_current_staff)):
    return current_staff


# ---------------------------------------------------------------------------
# Live data (no auth required — for display boards)
# ---------------------------------------------------------------------------

@router.get("/counters/live", response_model=list[CounterSchema])
async def get_live_counters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Counter))
    return result.scalars().all()


@router.get("/queues/live")
async def get_live_queues(db: AsyncSession = Depends(get_db)):
    """Returns per-service waiting count, currently serving, etc."""
    queues_res = await db.execute(select(Queue))
    queues = queues_res.scalars().all()

    out = []
    for q in queues:
        waiting_res = await db.execute(
            select(Token).where(Token.queue_id == q.id, Token.status == "WAITING")
        )
        waiting = waiting_res.scalars().all()
        out.append({
            "queue_id": q.id,
            "service_id": q.service_id,
            "waiting_count": len(waiting),
        })
    return out


@router.get("/services")
async def list_services(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service))
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Counter operations (auth required)
# ---------------------------------------------------------------------------

@router.post("/counters/{counter_id}/next")
async def call_next(
    counter_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_counter_staff),
):
    """
    Complete & Next: finishes current SERVING token, then calls next token.
    Checks for due recalls before calling a normal waiting customer.
    """
    try:
        next_token = await queue_manager.complete_and_next(
            db,
            counter_id=counter_id,
            actor_id=current_staff.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return {
        "message": "Done",
        "next_token_id": next_token.id if next_token else None,
        "next_display_number": next_token.display_number if next_token else None,
        "is_recall": (next_token.missed_counter_id is not None) if next_token else False,
    }


@router.post("/counters/{counter_id}/start")
async def start_service(
    counter_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_counter_staff),
):
    """
    Start Service: transitions CALLED → SERVING.
    Customer must be physically present.
    """
    try:
        token = await queue_manager.start_service(
            db,
            counter_id=counter_id,
            actor_id=current_staff.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return {
        "message": "Service started",
        "token_id": token.id,
        "display_number": token.display_number,
    }


@router.post("/counters/{counter_id}/missed")
async def mark_missed(
    counter_id: str,
    req: CommandRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Compatibility route using the same retry-safe command contract."""
    return await workstation_command(counter_id, "missed", req, db, current_staff)


@router.post("/counters/{counter_id}/absent-again")
async def mark_absent_again(
    counter_id: str,
    req: CommandRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Recall absence requires request identity and the expected attempt count."""
    return await workstation_command(counter_id, "absent-again", req, db, current_staff)
