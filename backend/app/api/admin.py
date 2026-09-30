"""Read-only admin monitoring. No customer details or queue mutations."""
import math
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import require_admin
from app.models.schema import Service, Queue, Counter, Token, Staff

router = APIRouter(prefix='/admin', tags=['admin'], dependencies=[Depends(require_admin)])
from app.api.allocations import router as allocations_router
router.include_router(allocations_router)

from app.api.demo_allocations import router as demo_allocations_router
router.include_router(demo_allocations_router)

CENTRE_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


@router.get('/monitor')
async def monitor(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    now = datetime.now(timezone.utc)
    day_start = now.astimezone(CENTRE_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    services = (await db.execute(select(Service, Queue.id).join(Queue, Queue.service_id == Service.id)
                                .order_by(Service.name))).all()
    counts = {(qid, status): count for qid, status, count in (await db.execute(
        select(Token.queue_id, Token.status, func.count()).group_by(Token.queue_id, Token.status))).all()}
    registered_today = (await db.execute(select(func.count()).select_from(Token).where(
        Token.registered_at >= day_start, Token.registered_at < day_end))).scalar_one()
    completed_today = (await db.execute(select(func.count()).select_from(Token).where(
        Token.status == 'COMPLETED', Token.completed_at >= day_start, Token.completed_at < day_end))).scalar_one()
    rows = (await db.execute(select(Counter, Staff.name, Token.display_number, Token.status)
        .outerjoin(Staff, Staff.id == Counter.staff_id).outerjoin(Token, Token.id == Counter.current_token_id)
        .order_by(Counter.label))).all()
    ranked = select(Token.id, Token.queue_id, Token.display_number,
        func.row_number().over(partition_by=Token.queue_id, order_by=(Token.sort_key, Token.id)).label('position')
        ).where(Token.status == 'WAITING').subquery()
    upcoming = {}
    for tid, qid, number in (await db.execute(select(ranked.c.id, ranked.c.queue_id, ranked.c.display_number)
                                             .where(ranked.c.position <= 3).order_by(ranked.c.position))).all():
        upcoming.setdefault(qid, []).append({'id': tid, 'display_number': number})
    names = {s.id: s.name for s, _ in services}
    counters = [{'id': c.id, 'label': c.label, 'service_name': names.get(c.service_id, 'Unassigned'),
        'queue_id': c.queue_id, 'status': c.status, 'staff_name': name,
        'token_number': number, 'token_status': status, 'serving_started_at': c.serving_started_at,
        'recorded_completions': c.served_today} for c, name, number, status in rows]
    queues = []
    for service, qid in services:
        assigned = [c for c, *_ in rows if c.queue_id == qid]
        active = [c for c in assigned if c.status == 'ACTIVE']
        waiting = counts.get((qid, 'WAITING'), 0)
        duration = sum(c.avg_service_time_sec or service.expected_duration_sec for c in active) / len(active) if active else None
        # Approximate time for the end of the waiting line, not a historical average.
        estimate = math.ceil((waiting + sum(c.current_token_id is not None for c in active)) * duration / len(active) / 60) if active else None
        queues.append({'id': qid, 'service_name': service.name, 'waiting': waiting,
            'missed': counts.get((qid, 'MISSED'), 0), 'called': counts.get((qid, 'CALLED'), 0),
            'serving': counts.get((qid, 'SERVING'), 0), 'active_counters': len(active),
            'total_counters': len(assigned), 'estimated_wait_minutes': estimate,
            'upcoming': upcoming.get(qid, [])})
    return {'server_time': now, 'report_date': day_start.date().isoformat(), 'timezone': 'Asia/Kolkata',
        'registered_today': registered_today, 'completed_today': completed_today,
        'waiting_now': sum(q['waiting'] for q in queues),
        'active_counters': sum(c['status'] == 'ACTIVE' for c in counters),
        'queues': queues, 'counters': counters}


@router.get('/analytics')
async def analytics(response: Response, date: str | None = None, db: AsyncSession = Depends(get_db)):
    """One centre-local calendar day. Only aggregate operational timestamps."""
    from datetime import date as calendar_date
    from fastapi import HTTPException
    from sqlalchemy import or_, and_
    response.headers['Cache-Control'] = 'no-store'
    now = datetime.now(timezone.utc)
    try:
        selected = calendar_date.fromisoformat(date) if date else now.astimezone(CENTRE_TIMEZONE).date()
    except ValueError as exc:
        raise HTTPException(422, 'Use a calendar date in YYYY-MM-DD format') from exc
    if selected > now.astimezone(CENTRE_TIMEZONE).date():
        raise HTTPException(422, 'Analytics are available for today or earlier dates')
    start = datetime.combine(selected, datetime.min.time(), tzinfo=CENTRE_TIMEZONE)
    end = start + timedelta(days=1)
    services = (await db.execute(select(Service.id, Service.name, Queue.id)
        .join(Queue, Queue.service_id == Service.id).order_by(Service.name))).all()
    def bucket():
        return {'registrations': 0, 'completions': 0, 'waits': [], 'durations': []}
    totals = bucket()
    hourly = [dict(hour=h, **bucket()) for h in range(24)]
    by_queue = {qid: dict(service_id=sid, service_name=name, **bucket()) for sid, name, qid in services}
    rows = (await db.execute(select(Token.queue_id, Token.status, Token.registered_at,
        Token.serving_started_at, Token.completed_at).where(or_(
            and_(Token.registered_at >= start, Token.registered_at < end),
            and_(Token.status == 'COMPLETED', Token.completed_at >= start, Token.completed_at < end)
        )))).all()
    for qid, status, registered, started, completed in rows:
        service = by_queue.get(qid)
        if registered is not None and start <= registered < end:
            for target in (totals, hourly[registered.astimezone(CENTRE_TIMEZONE).hour], service):
                if target is not None:
                    target['registrations'] += 1
        if status == 'COMPLETED' and completed is not None and start <= completed < end:
            for target in (totals, hourly[completed.astimezone(CENTRE_TIMEZONE).hour], service):
                if target is None:
                    continue
                target['completions'] += 1
                if started is not None and registered is not None and registered <= started <= completed:
                    target['waits'].append((started - registered).total_seconds())
                if started is not None and started <= completed:
                    target['durations'].append((completed - started).total_seconds())
    def summarize(b):
        waits, durations = b.pop('waits'), b.pop('durations')
        return {**b, 'avg_wait_seconds': round(sum(waits) / len(waits), 1) if waits else None,
                'wait_samples': len(waits),
                'avg_service_seconds': round(sum(durations) / len(durations), 1) if durations else None,
                'service_samples': len(durations)}
    return {'report_date': selected.isoformat(), 'timezone': 'Asia/Kolkata', 'server_time': now,
            'partial_day': selected == now.astimezone(CENTRE_TIMEZONE).date(),
            'summary': summarize(totals), 'hourly': [summarize(b) for b in hourly],
            'services': [summarize(b) for b in by_queue.values()],
            'utilization_percent': None,
            'utilization_note': 'Counter opening hours and complete pause history are not recorded.'}


@router.get('/predictions')
async def predictions(response: Response, db: AsyncSession = Depends(get_db)):
    from app.services.predictions import build_forecast, LOOKBACK_DAYS
    response.headers['Cache-Control'] = 'no-store'
    now = datetime.now(timezone.utc)
    end = now.astimezone(CENTRE_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=LOOKBACK_DAYS)
    local_time = func.timezone('Asia/Kolkata', Token.registered_at)
    day = func.date(local_time)
    hour = func.extract('hour', local_time)
    rows = (await db.execute(select(day, hour, Queue.service_id, func.count())
        .join(Queue, Queue.id == Token.queue_id)
        .where(Token.registered_at >= start, Token.registered_at < end)
        .group_by(day, hour, Queue.service_id))).all()
    services = (await db.execute(select(Service.id, Service.name).order_by(Service.name))).all()
    return build_forecast([(day, int(hour), sid, count) for day, hour, sid, count in rows], services, now)
