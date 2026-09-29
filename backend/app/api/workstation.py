"""Authenticated live workstation; commands are retry-safe and counter-scoped."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_staff
from app.models.schema import Counter, Queue, Token, Service, Staff
from app.services import queue_manager as qm
from app.services.commands import fingerprint, find_command, remember


def private_response(response: Response):
    response.headers['Cache-Control'] = 'no-store'


router = APIRouter(prefix='/staff', tags=['workstation'], dependencies=[Depends(private_response)])


def token_view(token):
    if token is None:
        return None
    return {'id': token.id, 'display_number': token.display_number, 'status': token.status,
            'serving_started_at': token.serving_started_at, 'is_recall': token.missed_counter_id is not None,
            'recall_attempts': token.recall_attempts, 'recall_ready': token.recall_ready}


@router.get('/workstation')
async def workstation(db: AsyncSession = Depends(get_db), staff: Staff = Depends(get_current_staff)):
    if staff.role != 'STAFF':
        raise HTTPException(403, 'Only counter staff can operate a workstation')
    counters = (await db.execute(select(Counter).where(Counter.staff_id == staff.id))).scalars().all()
    if len(counters) > 1:
        raise HTTPException(409, 'Multiple counters assigned. Ask your administrator to correct the assignment.')
    if not counters:
        return {'staff': {'id': staff.id, 'name': staff.name}, 'counter': None}
    counter = counters[0]
    service = await db.get(Service, counter.service_id)
    current = await db.get(Token, counter.current_token_id) if counter.current_token_id else None
    waiting = (await db.execute(select(Token).where(Token.queue_id == counter.queue_id,
        Token.status == 'WAITING').order_by(Token.sort_key).limit(3))).scalars().all()
    count = (await db.execute(select(func.count()).select_from(Token).where(
        Token.queue_id == counter.queue_id, Token.status == 'WAITING'))).scalar_one()
    missed = (await db.execute(select(Token).where(Token.missed_counter_id == counter.id,
        Token.status == 'MISSED').order_by(Token.missed_at, Token.id))).scalars().all()
    return {'staff': {'id': staff.id, 'name': staff.name},
            'counter': {'id': counter.id, 'label': counter.label, 'status': counter.status,
                        'service_name': service.name, 'served_today': counter.served_today},
            'current_token': token_view(current), 'upcoming': [token_view(t) for t in waiting],
            'waiting_count': count, 'missed': [token_view(t) for t in missed], 'server_time': qm._now()}


class CommandRequest(BaseModel):
    request_id: str = Field(min_length=16, max_length=128)
    expected_token_id: str | None
    expected_token_status: str | None
    expected_recall_attempts: int | None = Field(default=None, ge=0, le=2)


@router.post('/counters/{counter_id}/{action}')
async def command(counter_id: str, action: Literal['next', 'start', 'pause', 'resume', 'missed', 'absent-again'],
                  req: CommandRequest, db: AsyncSession = Depends(get_db),
                  staff: Staff = Depends(get_current_staff)):
    if staff.role != 'STAFF':
        raise HTTPException(403, 'Only counter staff can operate a workstation')
    owner = f'staff:{staff.id}'
    digest = fingerprint({'counter_id': counter_id, 'action': action,
                          'expected_token_id': req.expected_token_id,
                          'expected_token_status': req.expected_token_status,
                          **({'expected_recall_attempts': req.expected_recall_attempts}
                             if req.expected_recall_attempts is not None else {})})
    existing = await find_command(db, owner, req.request_id)
    queue_id = (await db.execute(select(Counter.queue_id).where(Counter.id == counter_id))).scalar_one_or_none()
    if queue_id is None:
        raise HTTPException(404, 'Counter not found')
    await db.execute(select(Queue).where(Queue.id == queue_id).with_for_update())
    counter = (await db.execute(select(Counter).where(Counter.id == counter_id)
        .with_for_update().execution_options(populate_existing=True))).scalar_one()
    if counter.staff_id != staff.id:
        raise HTTPException(403, 'This counter is not assigned to you')
    if existing:
        if existing.request_hash != digest:
            raise HTTPException(409, 'Request ID was already used for a different command')
        return existing.response_payload
    current = None
    if counter.current_token_id:
        current = (await db.execute(select(Token).where(Token.id == counter.current_token_id)
            .with_for_update().execution_options(populate_existing=True))).scalar_one()
    if counter.current_token_id != req.expected_token_id or (current.status if current else None) != req.expected_token_status:
        raise HTTPException(409, 'Counter state changed. Refresh before taking another action.')
    if counter.status == 'CLOSED':
        raise HTTPException(409, 'Counter is closed')
    if action == 'absent-again' and (current is None or
            req.expected_recall_attempts != current.recall_attempts):
        raise HTTPException(409, 'Recall changed. Refresh before marking absent.')
    try:
        if action == 'pause':
            counter.status = 'PAUSED'
        elif action == 'resume':
            counter.status = 'ACTIVE'
        elif action == 'start':
            if counter.status != 'ACTIVE':
                raise HTTPException(409, 'Resume the counter before starting service')
            await qm.start_service(db, counter_id=counter_id, actor_id=staff.id)
        elif action in ('missed', 'absent-again'):
            operation = qm.mark_missed if action == 'missed' else qm.mark_absent_again
            await operation(db, counter_id=counter_id, actor_id=staff.id)
        else:
            if counter.status != 'ACTIVE' and current is None:
                raise HTTPException(409, 'Resume the counter before calling a customer')
            await qm.complete_and_next(db, counter_id=counter_id, actor_id=staff.id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    response = {'action': action, 'counter_id': counter_id, 'current_token_id': counter.current_token_id,
                'counter_status': counter.status}
    remember(db, owner, req.request_id, digest, response)
    await db.commit()
    return response
