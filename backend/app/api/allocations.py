"""Admin scheduling and explicit safe counter handovers."""
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, AwareDatetime, Field, model_validator
from sqlalchemy import select, or_, func
from app.core.database import get_db
from app.core.deps import require_admin
from app.models.schema import StaffAllocation, Staff, Counter, Queue, EventLog

router = APIRouter(prefix='/allocations', dependencies=[Depends(require_admin)])

class AllocationRequest(BaseModel):
    id: str = Field(min_length=16, max_length=64)
    staff_id: str
    counter_id: str
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode='after')
    def valid_interval(self):
        if self.ends_at <= self.starts_at:
            raise ValueError('End must be after start')
        return self

def view(row):
    return {key: getattr(row, key) for key in ('id', 'staff_id', 'counter_id', 'starts_at', 'ends_at', 'status')}

async def lock(db):
    # Serialize scheduling, then use the same queue-before-counter lock order as dispatch.
    await db.execute(select(func.pg_advisory_xact_lock(714203861)))
    await db.execute(select(Queue).order_by(Queue.id).with_for_update())
    return (await db.execute(select(Counter).order_by(Counter.id).with_for_update()
        .execution_options(populate_existing=True))).scalars().all()

@router.get('')
async def listing(response: Response, db=Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    staff = (await db.execute(select(Staff).where(Staff.role == 'STAFF', Staff.is_active == True).order_by(Staff.name))).scalars().all()
    counters = (await db.execute(select(Counter).order_by(Counter.label))).scalars().all()
    rows = (await db.execute(select(StaffAllocation).order_by(StaffAllocation.starts_at.desc()))).scalars().all()
    return {'staff': [{'id': s.id, 'name': s.name} for s in staff],
        'counters': [{'id': c.id, 'label': c.label, 'staff_id': c.staff_id, 'busy': c.current_token_id is not None} for c in counters],
        'allocations': [view(r) for r in rows], 'server_time': datetime.now(timezone.utc)}

@router.post('')
async def schedule(req: AllocationRequest, db=Depends(get_db), admin=Depends(require_admin)):
    await lock(db)
    existing = await db.get(StaffAllocation, req.id)
    if existing:
        if any(getattr(existing, k) != getattr(req, k) for k in ('staff_id', 'counter_id', 'starts_at', 'ends_at')):
            raise HTTPException(409, 'Request ID already used for another allocation')
        return view(existing)
    staff = await db.get(Staff, req.staff_id)
    counter = await db.get(Counter, req.counter_id)
    if not staff or staff.role != 'STAFF' or not staff.is_active or not counter:
        raise HTTPException(422, 'Select an active staff member and valid counter')
    if req.ends_at <= datetime.now(timezone.utc):
        raise HTTPException(422, 'Allocation must end in the future')
    conflict = (await db.execute(select(StaffAllocation.id).where(
        StaffAllocation.status.in_(['SCHEDULED', 'ACTIVE']),
        StaffAllocation.starts_at < req.ends_at, StaffAllocation.ends_at > req.starts_at,
        or_(StaffAllocation.staff_id == req.staff_id, StaffAllocation.counter_id == req.counter_id)))).first()
    if conflict:
        raise HTTPException(409, 'Staff or counter already booked during this time')
    row = StaffAllocation(**req.model_dump(), status='SCHEDULED', created_by=admin.id)
    db.add(row)
    db.add(EventLog(entity_type='Staff', entity_id=staff.id, event_type='ALLOCATION_SCHEDULED', actor_id=admin.id,
        payload=req.model_dump(mode='json')))
    await db.commit()
    return view(row)

@router.post('/{allocation_id}/{action}')
async def handover(allocation_id: str, action: Literal['apply', 'release', 'cancel'], db=Depends(get_db), admin=Depends(require_admin)):
    counters = await lock(db)
    row = await db.get(StaffAllocation, allocation_id)
    if not row:
        raise HTTPException(404, 'Allocation not found')
    if (action == 'apply' and row.status == 'ACTIVE') or (action == 'release' and row.status == 'COMPLETED') or (action == 'cancel' and row.status == 'CANCELLED'):
        return view(row)
    target = next(c for c in counters if c.id == row.counter_id)
    now = datetime.now(timezone.utc)
    if action == 'cancel':
        if row.status != 'SCHEDULED':
            raise HTTPException(409, 'Only a scheduled allocation can be cancelled')
        row.status = 'CANCELLED'
    elif action == 'apply':
        if row.status != 'SCHEDULED' or not row.starts_at <= now < row.ends_at:
            raise HTTPException(409, 'Allocation is not due or has expired')
        staff = await db.get(Staff, row.staff_id)
        if not staff.is_active or staff.role != 'STAFF' or target.status == 'CLOSED':
            raise HTTPException(409, 'Staff or counter unavailable')
        sources = [c for c in counters if c.staff_id == row.staff_id]
        if len(sources) > 1:
            raise HTTPException(409, 'Staff has multiple existing counter assignments')
        active = (await db.execute(select(StaffAllocation).where(StaffAllocation.status == 'ACTIVE'))).scalars().all()
        involved = {target.id, *(c.id for c in sources)}
        if any(a.staff_id == row.staff_id or a.replaced_staff_id == row.staff_id or a.counter_id in involved or a.source_counter_id in involved for a in active):
            raise HTTPException(409, 'An active handover must be released first')
        if target.current_token_id or any(c.current_token_id for c in sources):
            raise HTTPException(409, 'Staff and both counters must be free before transfer')
        row.source_counter_id = sources[0].id if sources else None
        row.replaced_staff_id = target.staff_id
        for c in sources:
            c.staff_id = None
            if c.id != target.id:
                c.status = 'PAUSED'
        target.staff_id = row.staff_id
        row.status = 'ACTIVE'
    else:
        if row.status != 'ACTIVE':
            raise HTTPException(409, 'Only active allocations can be released')
        source = next((c for c in counters if c.id == row.source_counter_id), None)
        if target.current_token_id or (source and source.current_token_id):
            raise HTTPException(409, 'Finish the current customer before releasing staff')
        if target.staff_id != row.staff_id or (source and source.id != target.id and source.staff_id is not None):
            raise HTTPException(409, 'Counter assignment changed; resolve before release')
        target.staff_id = row.replaced_staff_id
        if source:
            source.staff_id = row.staff_id
        if target.staff_id is None:
            target.status = 'PAUSED'
        row.status = 'COMPLETED'
    db.add(EventLog(entity_type='Staff', entity_id=row.staff_id, event_type='ALLOCATION_' + action.upper(),
        actor_id=admin.id, payload={'allocation_id': row.id, 'counter_id': row.counter_id}))
    await db.commit()
    return view(row)
