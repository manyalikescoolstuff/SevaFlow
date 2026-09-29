"""Serialize duplicate requests before domain row locks and compare payloads."""
import hashlib
import json
from sqlalchemy import select, func
from app.models.schema import IdempotencyRecord

def fingerprint(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

async def find_command(db, owner, request_id):
    # Stable signed bigint; Python's hash() changes between processes.
    digest = hashlib.sha256(json.dumps([owner, request_id]).encode()).digest()
    lock_id = int.from_bytes(digest[:8], 'big', signed=True)
    await db.execute(select(func.pg_advisory_xact_lock(lock_id)))
    return (await db.execute(select(IdempotencyRecord).where(
        IdempotencyRecord.device_id == owner,
        IdempotencyRecord.hardware_request_id == request_id,
    ))).scalar_one_or_none()

def remember(db, owner, request_id, request_hash, response):
    db.add(IdempotencyRecord(device_id=owner, hardware_request_id=request_id,
        request_hash=request_hash, response_payload=response))
