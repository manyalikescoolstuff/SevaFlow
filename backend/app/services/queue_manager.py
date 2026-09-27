"""
QueueManager — all transactional queue mutations for SevaFlow.

Lock acquisition order (always consistent to prevent deadlocks):
  1. Queue (with_for_update)
  2. Counter (with_for_update)
  3. Token  (with_for_update)

Recall rules (approved):
  - MISSED token stays MISSED. missed_counter_id records the responsible counter.
  - recall_attempts: incremented only on an unsuccessful explicit recall attempt.
  - Original MISSED call is NOT counted as attempt 1.
  - After recall_attempts == 2 and another absence → status = CLOSED_MISSED.
  - Complete & Next checks for due recalls before calling normal waiting customers.
  - Multiple missed tokens (OPEN POLICY — see comments below).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import Counter, EventLog, Queue, Token

MAX_RECALL_ATTEMPTS = 2
RESERVATION_EXPIRY_MINUTES = 15


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _log(session: AsyncSession, entity_type: str, entity_id: str,
         event_type: str, payload: dict, actor_id: Optional[str] = None) -> None:
    """Append an EventLog row (written in same transaction as mutation)."""
    session.add(EventLog(
        id=str(uuid.uuid4()),
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        actor_id=actor_id,
        payload=payload,
    ))


# ---------------------------------------------------------------------------
# Hardware token reservation (Pico W → backend)
# ---------------------------------------------------------------------------

async def reserve_token(
    db: AsyncSession,
    *,
    service_id: str,
    hardware_reservation_id: str,
    display_number: str,
    claim_secret_hash: str,
    device_id: str,
) -> Token:
    """
    Create a RESERVED token from a Pico W request.
    Called only after idempotency check passes.
    Locks Queue row to ensure current_sequence is consistent.
    """
    # Lock queue for this service
    q_res = await db.execute(
        select(Queue).where(Queue.service_id == service_id).with_for_update()
    )
    queue = q_res.scalars().first()
    if not queue:
        raise ValueError(f"No queue for service {service_id}")

    token = Token(
        id=str(uuid.uuid4()),
        display_number=display_number,
        queue_id=queue.id,
        status="RESERVED",
        hardware_reservation_id=hardware_reservation_id,
        claim_secret_hash=claim_secret_hash,
        reservation_expires_at=_now() + timedelta(minutes=RESERVATION_EXPIRY_MINUTES),
        issued_at=_now(),
    )
    db.add(token)

    _log(db, "Token", token.id, "RESERVED", {
        "display_number": display_number,
        "hardware_reservation_id": hardware_reservation_id,
    }, actor_id=f"pico:{device_id}")

    return token


# ---------------------------------------------------------------------------
# Browser claim (first QR scan)
# ---------------------------------------------------------------------------

async def claim_token(
    db: AsyncSession,
    *,
    hardware_reservation_id: str,
    claim_secret_hash: str,
    recovery_credential_hash: str,
    browser_session_id: str,
) -> Token:
    """
    Transition RESERVED → CLAIMED.

    Rules:
    - Token must be RESERVED and not expired.
    - claim_secret_hash must match stored hash.
    - recovery_credential_hash (browser-generated before this call) is stored.
    - browser_session_id is the claim session ID (unique, stored on token).
    - Idempotent retry: if already CLAIMED with same browser_session_id, return token.
    - Another browser with only the QR cannot take over a CLAIMED token.
    """
    token_res = await db.execute(
        select(Token)
        .where(Token.hardware_reservation_id == hardware_reservation_id)
        .with_for_update()
    )
    token = token_res.scalars().first()

    if not token:
        raise ValueError("Token not found")

    # Idempotent retry from same browser
    if token.status == "CLAIMED":
        if token.claim_session_id == browser_session_id:
            return token  # safe retry
        raise PermissionError("Token already claimed by another browser")

    if token.status != "RESERVED":
        raise ValueError(f"Token is in state {token.status}, cannot claim")

    if token.claim_secret_hash != claim_secret_hash:
        raise PermissionError("Invalid claim secret")

    if token.reservation_expires_at < _now():
        token.status = "EXPIRED"
        _log(db, "Token", token.id, "EXPIRED", {"reason": "claim_attempted_after_expiry"})
        raise ValueError("Reservation expired")

    token.status = "CLAIMED"
    token.claim_session_id = browser_session_id
    token.recovery_credential_hash = recovery_credential_hash
    token.claimed_at = _now()

    _log(db, "Token", token.id, "CLAIMED", {
        "hardware_reservation_id": hardware_reservation_id,
    })

    return token


# ---------------------------------------------------------------------------
# Registration (form submission → WAITING)
# ---------------------------------------------------------------------------

async def register_token(
    db: AsyncSession,
    *,
    token_id: str,
    claim_session_id: str,
    tracking_secret_hash: str,
    customer_name: str,
) -> Token:
    """
    Transition CLAIMED → WAITING.
    Allocates immutable scan_sequence and initial sort_key under Queue lock.

    Idempotent: if already WAITING with same claim_session_id, return token.
    """
    # Lock token first (token id known, safe starting point)
    tok_res = await db.execute(
        select(Token).where(Token.id == token_id).with_for_update()
    )
    token = tok_res.scalars().first()
    if not token:
        raise ValueError("Token not found")

    if token.status == "WAITING":
        if token.claim_session_id == claim_session_id:
            return token  # idempotent retry
        raise PermissionError("Session mismatch on registration retry")

    if token.status != "CLAIMED":
        raise ValueError(f"Token in state {token.status}, cannot register")

    if token.claim_session_id != claim_session_id:
        raise PermissionError("Invalid claim session")

    if token.reservation_expires_at < _now():
        token.status = "EXPIRED"
        _log(db, "Token", token.id, "EXPIRED", {"reason": "registration_after_expiry"})
        raise ValueError("Reservation expired")

    # Lock queue for sequence/sort_key allocation
    q_res = await db.execute(
        select(Queue).where(Queue.id == token.queue_id).with_for_update()
    )
    queue = q_res.scalars().first()

    queue.current_sequence += 1
    seq = queue.current_sequence

    token.status = "WAITING"
    token.scan_sequence = seq
    token.sort_key = seq  # initial sort_key equals scan_sequence
    token.tracking_secret_hash = tracking_secret_hash
    token.registered_at = _now()

    _log(db, "Token", token.id, "WAITING", {
        "scan_sequence": seq,
        "sort_key": seq,
        "customer_name": customer_name,
    })

    return token


# ---------------------------------------------------------------------------
# Complete & Next (staff action)
# ---------------------------------------------------------------------------

async def complete_and_next(
    db: AsyncSession,
    *,
    counter_id: str,
    actor_id: str,
) -> Optional[Token]:
    """
    Mark current token COMPLETED (must be SERVING).
    Then:
      1. Check for any MISSED tokens assigned to this counter that are due for recall.
         - Due = missed_counter_id == counter_id AND status == MISSED
         - POLICY (SINGLE missed token): recall that token next.
         - POLICY (MULTIPLE missed tokens): OPEN — see comments below.
      2. If no recall due, call the next WAITING token (by sort_key ASC).
      3. Update counter.current_token_id and counter.served_today.

    Locking order: Queue → Counter → Token
    """
    # Lock counter
    ctr_res = await db.execute(
        select(Counter).where(Counter.id == counter_id).with_for_update()
    )
    counter = ctr_res.scalars().first()
    if not counter:
        raise ValueError("Counter not found")

    now = _now()

    # --- Step 1: Complete current token ---
    if counter.current_token_id:
        tok_res = await db.execute(
            select(Token).where(Token.id == counter.current_token_id).with_for_update()
        )
        current = tok_res.scalars().first()
        if current:
            if current.status != "SERVING":
                raise ValueError(f"Current token is {current.status}, not SERVING")
            # Update average service time
            if counter.serving_started_at:
                duration = int((now - counter.serving_started_at).total_seconds())
                if counter.served_today == 0:
                    counter.avg_service_time_sec = duration
                else:
                    counter.avg_service_time_sec = (
                        (counter.avg_service_time_sec * counter.served_today + duration)
                        // (counter.served_today + 1)
                    )
            current.status = "COMPLETED"
            current.completed_at = now
            counter.served_today += 1
            _log(db, "Token", current.id, "COMPLETED", {}, actor_id=actor_id)

    counter.current_token_id = None
    counter.serving_started_at = None

    # --- Step 2: Check for due recalls ---
    # APPROVED POLICY: Recall missed tokens assigned to THIS counter.
    #
    # OPEN QUESTION — Multiple missed tokens:
    # If more than one MISSED token is due (missed_counter_id == this counter),
    # we currently recall ALL of them in FIFO order (by missed_at).
    # Proposed behaviour:
    #   a) Recall first due missed token → call it (status → CALLED).
    #   b) If it becomes SERVING, the next recall triggers after that service completes.
    #   c) If absent (Mark Absent Again) → increment recall_attempts, then immediately
    #      recall next due missed token (if any), BEFORE calling a normal waiting customer.
    #   d) Only after all due missed tokens have had one recall attempt each does the
    #      counter call the next normal waiting customer.
    # *** This multi-missed behaviour is NOT yet approved — flagged for review. ***
    #
    # For now: recall the OLDEST due missed token (FIFO by missed_at), one at a time.

    missed_res = await db.execute(
        select(Token)
        .where(
            Token.missed_counter_id == counter_id,
            Token.status == "MISSED",
        )
        .order_by(Token.missed_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    recall_token = missed_res.scalars().first()

    if recall_token:
        recall_token.status = "CALLED"
        recall_token.called_at = now
        counter.current_token_id = recall_token.id
        counter.serving_started_at = None
        _log(db, "Token", recall_token.id, "RECALL_CALLED", {
            "recall_attempt_number": recall_token.recall_attempts + 1,
            "counter_id": counter_id,
        }, actor_id=actor_id)
        return recall_token

    # --- Step 3: No recall due — call next WAITING token ---
    return await _call_next_waiting(db, counter, actor_id, now)


async def _call_next_waiting(
    db: AsyncSession,
    counter: Counter,
    actor_id: str,
    now: datetime,
) -> Optional[Token]:
    """Pull the next WAITING token from queue by sort_key and mark it CALLED."""
    next_res = await db.execute(
        select(Token)
        .where(
            Token.queue_id == counter.queue_id,
            Token.status == "WAITING",
        )
        .order_by(Token.sort_key.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    next_token = next_res.scalars().first()

    if next_token:
        next_token.status = "CALLED"
        next_token.called_at = now
        counter.current_token_id = next_token.id
        counter.serving_started_at = None
        _log(db, "Token", next_token.id, "CALLED", {
            "counter_id": counter.id,
        }, actor_id=actor_id)

    return next_token


# ---------------------------------------------------------------------------
# Start Service (staff action)
# ---------------------------------------------------------------------------

async def start_service(
    db: AsyncSession,
    *,
    counter_id: str,
    actor_id: str,
) -> Token:
    """
    Transition current token CALLED → SERVING.
    Customer must be physically present.
    """
    ctr_res = await db.execute(
        select(Counter).where(Counter.id == counter_id).with_for_update()
    )
    counter = ctr_res.scalars().first()
    if not counter or not counter.current_token_id:
        raise ValueError("No active token at this counter")

    tok_res = await db.execute(
        select(Token).where(Token.id == counter.current_token_id).with_for_update()
    )
    token = tok_res.scalars().first()
    if not token or token.status != "CALLED":
        raise ValueError(f"Token is {token.status if token else 'missing'}, not CALLED")

    token.status = "SERVING"
    token.serving_started_at = _now()
    counter.serving_started_at = token.serving_started_at

    _log(db, "Token", token.id, "SERVING_STARTED", {
        "counter_id": counter_id,
    }, actor_id=actor_id)

    return token


# ---------------------------------------------------------------------------
# Mark Missed (first call — not a recall attempt)
# ---------------------------------------------------------------------------

async def mark_missed(
    db: AsyncSession,
    *,
    counter_id: str,
    actor_id: str,
) -> Optional[Token]:
    """
    Current token (must be CALLED) → MISSED.
    Sets missed_counter_id = this counter.
    recall_attempts stays at 0 (original miss is not a recall attempt).
    Then calls next WAITING token (recall check not triggered here —
    recalls are only triggered by complete_and_next).
    """
    ctr_res = await db.execute(
        select(Counter).where(Counter.id == counter_id).with_for_update()
    )
    counter = ctr_res.scalars().first()
    if not counter or not counter.current_token_id:
        raise ValueError("No active token at this counter")

    tok_res = await db.execute(
        select(Token).where(Token.id == counter.current_token_id).with_for_update()
    )
    token = tok_res.scalars().first()
    if not token or token.status != "CALLED":
        raise ValueError(f"Token is {token.status if token else 'missing'}, not CALLED")

    now = _now()
    token.status = "MISSED"
    token.missed_at = now
    token.missed_counter_id = counter_id
    # recall_attempts unchanged — stays at 0

    counter.current_token_id = None
    counter.serving_started_at = None

    _log(db, "Token", token.id, "MISSED", {
        "counter_id": counter_id,
        "recall_attempts_remaining": MAX_RECALL_ATTEMPTS - token.recall_attempts,
    }, actor_id=actor_id)

    # Call next WAITING token immediately (no recall check here)
    return await _call_next_waiting(db, counter, actor_id, now)


# ---------------------------------------------------------------------------
# Mark Absent Again (during a recall — counts as one recall attempt)
# ---------------------------------------------------------------------------

async def mark_absent_again(
    db: AsyncSession,
    *,
    counter_id: str,
    actor_id: str,
) -> Optional[Token]:
    """
    Staff confirms customer absent during a recall (token is CALLED, was MISSED).
    Increments recall_attempts.
    If recall_attempts reaches MAX_RECALL_ATTEMPTS → CLOSED_MISSED.
    Else → back to MISSED, check for another due missed token immediately.
    """
    ctr_res = await db.execute(
        select(Counter).where(Counter.id == counter_id).with_for_update()
    )
    counter = ctr_res.scalars().first()
    if not counter or not counter.current_token_id:
        raise ValueError("No active token at this counter")

    tok_res = await db.execute(
        select(Token).where(Token.id == counter.current_token_id).with_for_update()
    )
    token = tok_res.scalars().first()
    if not token or token.status != "CALLED":
        raise ValueError(f"Token is {token.status if token else 'missing'}, not CALLED")

    # Verify this was indeed a recalled (previously MISSED) token
    if token.missed_counter_id is None:
        raise ValueError("Token was not previously missed — use mark_missed instead")

    now = _now()
    token.recall_attempts += 1

    if token.recall_attempts >= MAX_RECALL_ATTEMPTS:
        token.status = "CLOSED_MISSED"
        token.completed_at = now
        _log(db, "Token", token.id, "CLOSED_MISSED", {
            "reason": "Two recall opportunities missed",
            "counter_id": counter_id,
        }, actor_id=actor_id)
    else:
        token.status = "MISSED"
        token.missed_at = now  # refresh timestamp for next recall ordering
        _log(db, "Token", token.id, "RECALL_MISSED", {
            "recall_attempts": token.recall_attempts,
            "remaining": MAX_RECALL_ATTEMPTS - token.recall_attempts,
        }, actor_id=actor_id)

    counter.current_token_id = None
    counter.serving_started_at = None

    # Check for another due missed token before calling next normal customer
    # (OPEN POLICY for multiple missed tokens — same FIFO approach as complete_and_next)
    missed_res = await db.execute(
        select(Token)
        .where(
            Token.missed_counter_id == counter_id,
            Token.status == "MISSED",
        )
        .order_by(Token.missed_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    next_recall = missed_res.scalars().first()

    if next_recall:
        next_recall.status = "CALLED"
        next_recall.called_at = now
        counter.current_token_id = next_recall.id
        _log(db, "Token", next_recall.id, "RECALL_CALLED", {
            "recall_attempt_number": next_recall.recall_attempts + 1,
        }, actor_id=actor_id)
        return next_recall

    # No more recalls due — call next normal waiting customer
    return await _call_next_waiting(db, counter, actor_id, now)
