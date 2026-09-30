from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, AwareDatetime, Field, model_validator
from app.core.deps import require_admin
from app.core.config import settings

router = APIRouter(prefix='/demo-allocations', dependencies=[Depends(require_admin)])

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

def _now():
    return datetime.now(timezone.utc)

def seed_demo_data():
    now = _now()
    return {
        "staff": [
            {"id": "dstf-01", "name": "Jane D. (Demo)", "role": "STAFF", "is_active": True},
            {"id": "dstf-02", "name": "John S. (Demo)", "role": "STAFF", "is_active": True},
            {"id": "dstf-03", "name": "Alice M. (Demo)", "role": "STAFF", "is_active": True},
        ],
        "counters": [
            {"id": "dctr-01", "label": "Demo Counter 1", "staff_id": "dstf-01", "busy": False},
            {"id": "dctr-02", "label": "Demo Counter 2", "staff_id": None, "busy": False},
            {"id": "dctr-03", "label": "Demo Counter 3", "staff_id": "dstf-02", "busy": True},
        ],
        "allocations": [
            # Active (needs release, overdue)
            {
                "id": "dalloc-01", "staff_id": "dstf-01", "counter_id": "dctr-01",
                "starts_at": now - timedelta(hours=2), "ends_at": now - timedelta(minutes=10),
                "status": "ACTIVE", "source_counter_id": "dctr-02", "replaced_staff_id": None
            },
            # Scheduled (due)
            {
                "id": "dalloc-02", "staff_id": "dstf-03", "counter_id": "dctr-02",
                "starts_at": now - timedelta(minutes=5), "ends_at": now + timedelta(minutes=55),
                "status": "SCHEDULED", "source_counter_id": None, "replaced_staff_id": None
            },
            # Scheduled (future)
            {
                "id": "dalloc-03", "staff_id": "dstf-02", "counter_id": "dctr-02",
                "starts_at": now + timedelta(hours=1), "ends_at": now + timedelta(hours=2),
                "status": "SCHEDULED", "source_counter_id": None, "replaced_staff_id": None
            },
            # History
            {
                "id": "dalloc-04", "staff_id": "dstf-01", "counter_id": "dctr-03",
                "starts_at": now - timedelta(days=1), "ends_at": now - timedelta(days=1, hours=-1),
                "status": "COMPLETED", "source_counter_id": None, "replaced_staff_id": None
            },
            # Expired Schedule
            {
                "id": "dalloc-05", "staff_id": "dstf-02", "counter_id": "dctr-01",
                "starts_at": now - timedelta(hours=3), "ends_at": now - timedelta(hours=2),
                "status": "SCHEDULED", "source_counter_id": None, "replaced_staff_id": None
            }
        ]
    }

DEMO_STATE = None

def get_demo_state():
    global DEMO_STATE
    if DEMO_STATE is None:
        DEMO_STATE = seed_demo_data()
    return DEMO_STATE

def reset_demo_state():
    global DEMO_STATE
    DEMO_STATE = seed_demo_data()
    return DEMO_STATE

@router.get('')
async def listing(response: Response):
    if not settings.ENABLE_DEMO_MODE:
        raise HTTPException(404, 'Demo mode is disabled')
    response.headers['Cache-Control'] = 'no-store'
    state = get_demo_state()
    return {
        'staff': [{'id': s['id'], 'name': s['name']} for s in state['staff']],
        'counters': [{'id': c['id'], 'label': c['label'], 'staff_id': c['staff_id'], 'busy': c['busy']} for c in state['counters']],
        'allocations': [{k: v for k, v in a.items() if k in ('id', 'staff_id', 'counter_id', 'starts_at', 'ends_at', 'status')} for a in sorted(state['allocations'], key=lambda x: x['starts_at'], reverse=True)],
        'server_time': datetime.now(timezone.utc)
    }

@router.post('')
async def schedule(req: AllocationRequest, admin=Depends(require_admin)):
    if not settings.ENABLE_DEMO_MODE:
        raise HTTPException(404, 'Demo mode is disabled')
    state = get_demo_state()
    for a in state['allocations']:
        if a['id'] == req.id:
            if a['staff_id'] != req.staff_id or a['counter_id'] != req.counter_id or a['starts_at'] != req.starts_at or a['ends_at'] != req.ends_at:
                raise HTTPException(409, 'Request ID already used for another allocation')
            return {k: v for k, v in a.items() if k in ('id', 'staff_id', 'counter_id', 'starts_at', 'ends_at', 'status')}
    
    staff = next((s for s in state['staff'] if s['id'] == req.staff_id), None)
    counter = next((c for c in state['counters'] if c['id'] == req.counter_id), None)
    if not staff or staff['role'] != 'STAFF' or not staff['is_active'] or not counter:
        raise HTTPException(422, 'Select an active staff member and valid counter')
    if req.ends_at <= datetime.now(timezone.utc):
        raise HTTPException(422, 'Allocation must end in the future')
    
    for a in state['allocations']:
        if a['status'] in ('SCHEDULED', 'ACTIVE') and a['starts_at'] < req.ends_at and a['ends_at'] > req.starts_at:
            if a['staff_id'] == req.staff_id or a['counter_id'] == req.counter_id:
                raise HTTPException(409, 'Staff or counter already booked during this time')
    
    new_alloc = {
        'id': req.id, 'staff_id': req.staff_id, 'counter_id': req.counter_id,
        'starts_at': req.starts_at, 'ends_at': req.ends_at, 'status': 'SCHEDULED',
        'source_counter_id': None, 'replaced_staff_id': None
    }
    state['allocations'].append(new_alloc)
    return {k: v for k, v in new_alloc.items() if k in ('id', 'staff_id', 'counter_id', 'starts_at', 'ends_at', 'status')}

@router.post('/{allocation_id}/{action}')
async def handover(allocation_id: str, action: Literal['apply', 'release', 'cancel'], admin=Depends(require_admin)):
    if not settings.ENABLE_DEMO_MODE:
        raise HTTPException(404, 'Demo mode is disabled')
    state = get_demo_state()
    row = next((a for a in state['allocations'] if a['id'] == allocation_id), None)
    if not row:
        raise HTTPException(404, 'Allocation not found')
    
    def view(r):
        return {k: v for k, v in r.items() if k in ('id', 'staff_id', 'counter_id', 'starts_at', 'ends_at', 'status')}
        
    if (action == 'apply' and row['status'] == 'ACTIVE') or (action == 'release' and row['status'] == 'COMPLETED') or (action == 'cancel' and row['status'] == 'CANCELLED'):
        return view(row)
        
    target = next(c for c in state['counters'] if c['id'] == row['counter_id'])
    now = datetime.now(timezone.utc)
    
    if action == 'cancel':
        if row['status'] != 'SCHEDULED':
            raise HTTPException(409, 'Only a scheduled allocation can be cancelled')
        row['status'] = 'CANCELLED'
    elif action == 'apply':
        if row['status'] != 'SCHEDULED' or not (row['starts_at'] <= now < row['ends_at']):
            raise HTTPException(409, 'Allocation is not due or has expired')
        staff = next((s for s in state['staff'] if s['id'] == row['staff_id']), None)
        if not staff or not staff['is_active']:
            raise HTTPException(409, 'Staff or counter unavailable')
        
        sources = [c for c in state['counters'] if c['staff_id'] == row['staff_id']]
        if len(sources) > 1:
            raise HTTPException(409, 'Staff has multiple existing counter assignments')
            
        involved = {target['id']} | {c['id'] for c in sources}
        active_allocs = [a for a in state['allocations'] if a['status'] == 'ACTIVE']
        for a in active_allocs:
            if a['staff_id'] == row['staff_id'] or a['replaced_staff_id'] == row['staff_id'] or a['counter_id'] in involved or a['source_counter_id'] in involved:
                raise HTTPException(409, 'An active handover must be released first')
                
        if target['busy'] or any(c['busy'] for c in sources):
            raise HTTPException(409, 'Staff and both counters must be free before transfer')
            
        row['source_counter_id'] = sources[0]['id'] if sources else None
        row['replaced_staff_id'] = target['staff_id']
        
        for c in sources:
            c['staff_id'] = None
        target['staff_id'] = row['staff_id']
        row['status'] = 'ACTIVE'
    else:
        if row['status'] != 'ACTIVE':
            raise HTTPException(409, 'Only active allocations can be released')
        source = next((c for c in state['counters'] if c['id'] == row['source_counter_id']), None)
        if target['busy'] or (source and source['busy']):
            raise HTTPException(409, 'Finish the current customer before releasing staff')
        if target['staff_id'] != row['staff_id'] or (source and source['id'] != target['id'] and source['staff_id'] is not None):
            raise HTTPException(409, 'Counter assignment changed; resolve before release')
            
        target['staff_id'] = row['replaced_staff_id']
        if source:
            source['staff_id'] = row['staff_id']
        row['status'] = 'COMPLETED'
        
    return view(row)

@router.post('/reset')
async def reset_demo(admin=Depends(require_admin)):
    if not settings.ENABLE_DEMO_MODE:
        raise HTTPException(404, 'Demo mode is disabled')
    reset_demo_state()
    return {"status": "ok"}
