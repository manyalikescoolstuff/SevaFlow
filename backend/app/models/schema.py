"""
SevaFlow SQLAlchemy Models — matches approved architecture.

Token lifecycle:
  RESERVED → CLAIMED → WAITING → CALLED → SERVING → COMPLETED
                                                    ↘ MISSED (recall_attempts < 2)
                                                    ↘ EXPIRED / CANCELLED

Recall: MISSED token stays MISSED between recall opportunities.
        recall_attempts increments per unsuccessful recall attempt (max 2).
        After 2 unsuccessful recalls → CLOSED_MISSED.

Counter.current_token_id is the single authoritative active assignment.
No counter_id column on Token — assignment is read via Counter.current_token_id.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey,
    Index, Integer, String, UniqueConstraint, event,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


def _now():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

class IdempotencyRecord(Base):
    """
    Stores the response for each (device_id, hardware_request_id) pair so that
    a Pico W retransmission gets the exact same response without a new token
    being created.
    """
    __tablename__ = "idempotency_records"

    id = Column(String, primary_key=True, default=_uuid)
    device_id = Column(String, nullable=False, index=True)
    hardware_request_id = Column(String, nullable=False, index=True)
    response_payload = Column(JSONB, nullable=False)
    request_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        UniqueConstraint("device_id", "hardware_request_id", name="uq_idempotency_device_request"),
    )


# ---------------------------------------------------------------------------
# Service & Queue
# ---------------------------------------------------------------------------

class Service(Base):
    __tablename__ = "services"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    expected_duration_sec = Column(Integer, nullable=False, default=300)

    queues = relationship("Queue", back_populates="service", uselist=False)
    counters = relationship("Counter", back_populates="service")


class Queue(Base):
    """
    One queue per service.  `current_sequence` is a BIGINT counter incremented
    atomically under a row lock to allocate scan_sequence values.
    """
    __tablename__ = "queues"

    id = Column(String, primary_key=True, default=_uuid)
    service_id = Column(String, ForeignKey("services.id"), nullable=False, unique=True)

    # Monotonically increasing counter for scan_sequence allocation
    current_sequence = Column(BigInteger, nullable=False, default=0)

    service = relationship("Service", back_populates="queues")
    tokens = relationship("Token", back_populates="queue")
    counters = relationship("Counter", back_populates="queue")


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

class Token(Base):
    """
    Token lifecycle states:
      RESERVED  – created by Pico, not yet claimed by a browser
      CLAIMED   – browser has locked this token (claim_session_id set)
      WAITING   – customer registered; has scan_sequence & sort_key
      CALLED    – staff has called this token
      SERVING   – Start Service pressed; service in progress
      COMPLETED – service finished successfully
      MISSED    – customer absent when called; recall_attempts < 2
      CLOSED_MISSED – recall_attempts == 2; customer must get new token
      EXPIRED   – reservation expired before claim/registration
      CANCELLED – cancelled by staff or customer

    Recall logic:
      When a token is missed:
        missed_counter_id records the counter that missed them.
        recall_attempts stays at its current value (0 for first miss).
      On each recall attempt:
        If staff marks absent → recall_attempts += 1, status stays MISSED.
        If recall_attempts reaches 2 → status = CLOSED_MISSED.
      The original MISSED event is NOT counted as a recall attempt.
    """
    __tablename__ = "tokens"

    id = Column(String, primary_key=True, default=_uuid)
    display_number = Column(String, nullable=False, index=True)
    queue_id = Column(String, ForeignKey("queues.id"), nullable=False, index=True)

    status = Column(String, nullable=False, index=True)  # see lifecycle above

    # Hardware-generated identifiers
    hardware_reservation_id = Column(String, unique=True, nullable=False, index=True)

    # SHA-256 hash of the QR claim secret (Pico-generated, never stored raw)
    claim_secret_hash = Column(String, nullable=False)

    # Browser recovery: browser generates recovery_credential before first claim.
    # SHA-256 hash stored here. Required for claim retries.
    recovery_credential_hash = Column(String, nullable=True)

    # Set when browser successfully claims (RESERVED → CLAIMED)
    claim_session_id = Column(String, nullable=True, unique=True)

    # Set when customer registers (CLAIMED → WAITING)
    tracking_secret_hash = Column(String, nullable=True)

    customer_name = Column(String(120), nullable=True)
    phone_number = Column(String(10), nullable=True)

    # Queue ordering — allocated once under Queue row lock on successful claim
    scan_sequence = Column(BigInteger, nullable=True, index=True)  # immutable first-scan order
    sort_key = Column(BigInteger, nullable=True, index=True)        # mutable queue position

    # Recall tracking
    recall_attempts = Column(Integer, nullable=False, default=0)
    recall_ready = Column(Boolean, nullable=False, default=False, server_default='false')
    missed_at = Column(DateTime(timezone=True), nullable=True)
    missed_counter_id = Column(String, ForeignKey("counters.id"), nullable=True)

    # Timestamps
    reservation_expires_at = Column(DateTime(timezone=True), nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    registered_at = Column(DateTime(timezone=True), nullable=True)
    called_at = Column(DateTime(timezone=True), nullable=True)
    serving_started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    queue = relationship("Queue", back_populates="tokens")
    missed_counter = relationship("Counter", foreign_keys=[missed_counter_id])


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------

class Staff(Base):
    __tablename__ = "staff"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="STAFF")  # STAFF | ADMIN
    is_active = Column(Boolean, nullable=False, default=True)

    counter = relationship("Counter", back_populates="staff", uselist=False)


# ---------------------------------------------------------------------------
# Counter
# ---------------------------------------------------------------------------

class Counter(Base):
    """
    current_token_id is the single source of truth for what token is active.
    A partial unique index guarantees at most one counter can own any token.
    """
    __tablename__ = "counters"

    id = Column(String, primary_key=True, default=_uuid)
    label = Column(String, nullable=False)
    service_id = Column(String, ForeignKey("services.id"), nullable=False)
    queue_id = Column(String, ForeignKey("queues.id"), nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE | PAUSED | CLOSED

    staff_id = Column(String, ForeignKey("staff.id"), nullable=True)
    current_token_id = Column(String, ForeignKey("tokens.id"), nullable=True)

    served_today = Column(Integer, nullable=False, default=0)
    avg_service_time_sec = Column(Integer, nullable=False, default=0)
    serving_started_at = Column(DateTime(timezone=True), nullable=True)

    service = relationship("Service", back_populates="counters")
    queue = relationship("Queue", back_populates="counters")
    current_token = relationship("Token", foreign_keys=[current_token_id])
    staff = relationship("Staff", back_populates="counter", foreign_keys=[staff_id])


# ---------------------------------------------------------------------------
# Event Log
# ---------------------------------------------------------------------------

class EventLog(Base):
    """
    Immutable audit log for every state transition.
    Written in the same transaction as the mutation it records.
    """
    __tablename__ = "event_logs"

    id = Column(String, primary_key=True, default=_uuid)
    entity_type = Column(String, nullable=False)  # Token | Counter | Staff
    entity_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    actor_id = Column(String, nullable=True)       # staff_id or "pico:<device_id>"
    payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

# Guarantees: at most one counter holds any given token
Index(
    "ix_counter_active_token",
    Counter.current_token_id,
    unique=True,
    postgresql_where=(Counter.current_token_id.isnot(None)),
)

# Fast lookup of WAITING tokens in queue order
Index("ix_token_queue_status_sort", Token.queue_id, Token.status, Token.sort_key)

# Fast lookup of MISSED tokens by their missed counter
Index("ix_token_missed_counter", Token.missed_counter_id, Token.missed_at,
      postgresql_where=(Token.status.in_(["MISSED"])))
