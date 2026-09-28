"""Real PostgreSQL contract tests, isolated in a disposable per-test schema.

Run from backend: python -B -m pytest tests/test_customer_contract.py -q
Uses TEST_DATABASE_URL if set, otherwise configured local DATABASE_URL.
Never alters the application's public schema or existing tokens.
"""
import asyncio
import os
import uuid
from datetime import timedelta

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.api.customer import router
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.schema import Service, Queue, Token, Counter
from app.services import queue_manager as qm


@pytest_asyncio.fixture
async def contract():
    schema = 'test_customer_' + uuid.uuid4().hex
    url = os.getenv('TEST_DATABASE_URL', settings.DATABASE_URL)
    admin = create_async_engine(url)
    async with admin.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={'server_settings': {'search_path': schema}})
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions.begin() as db:
            db.add(Service(id='service', name='Aadhaar', expected_duration_sec=300))
            await db.flush()
            db.add(Queue(id='queue', service_id='service', current_sequence=0))
            await db.flush()
            db.add(Counter(id='counter', label='Counter 1', queue_id='queue', service_id='service'))
            for n in range(4):
                db.add(Token(id=f't{n}', display_number=f'A{24+n:03}', queue_id='queue',
                    status='RESERVED', hardware_reservation_id=f'r{n}', claim_secret_hash='a'*64,
                    reservation_expires_at=qm._now()+timedelta(minutes=5)))
        app = FastAPI()
        app.include_router(router, prefix='/api/v1')
        async def database():
            async with sessions() as db:
                try:
                    yield db
                finally:
                    await db.rollback()
        app.dependency_overrides[get_db] = database
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test/api/v1/customer') as client:
            yield client, sessions, engine
    finally:
        await engine.dispose()
        # schema is generated here, never accepted from configuration/user input.
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


def claim(n=0):
    return dict(hardware_reservation_id=f'r{n}', claim_secret_hash='a'*64,
        browser_session_id=f'browser-session-{n:03}', recovery_credential_hash='b'*64,
        service_id='service', display_number=f'A{24+n:03}')


def recovery(n=0):
    return dict(token_id=f't{n}', claim_session_id=f'browser-session-{n:03}', recovery_credential_hash='b'*64)


def registration(n=0):
    return dict(**recovery(n), tracking_secret_hash='c'*64, customer_name='Manya Kumar', phone_number='9876543210')


async def test_scan_order_survives_reverse_registration_and_retries(contract):
    client, sessions, _ = contract
    first = (await client.post('/claim', json=claim())).json()
    second = (await client.post('/claim', json=claim(1))).json()
    assert (first['scan_sequence'], second['scan_sequence']) == (1, 2)
    assert first['status'] == 'CLAIMED'
    async with sessions.begin() as db:
        counter = await db.get(Counter, 'counter')
        assert await qm._call_next_waiting(db, counter, 'staff', qm._now()) is None
    assert (await client.post('/register', json=registration(1))).status_code == 200
    assert (await client.post('/register', json=registration())).status_code == 200
    again = (await client.post('/claim', json=claim())).json()
    assert again['scan_sequence'] == 1
    assert again['reservation_expires_at'] == first['reservation_expires_at']
    async with sessions.begin() as db:
        counter = await db.get(Counter, 'counter')
        selected = await qm._call_next_waiting(db, counter, 'staff', qm._now())
        assert selected.id == 't0'
    retry = await client.post('/register', json=registration())
    assert retry.status_code == 200 and retry.json()['status'] == 'CALLED'
    assert (await client.post('/register', json={**registration(), 'customer_name':'Someone Else'})).status_code == 409


async def test_later_registered_can_dispatch_while_earlier_still_typing(contract):
    client, sessions, _ = contract
    await client.post('/claim', json=claim())
    await client.post('/claim', json=claim(1))
    await client.post('/register', json=registration(1))
    async with sessions.begin() as db:
        counter = await db.get(Counter, 'counter')
        assert (await qm._call_next_waiting(db, counter, 'staff', qm._now())).id == 't1'
    await client.post('/register', json=registration())
    async with sessions() as db:
        assert (await db.get(Counter, 'counter')).current_token_id == 't1'
        assert (await db.get(Token, 't0')).scan_sequence == 1


async def test_concurrent_claims_and_lost_response_recovery(contract):
    client, sessions, _ = contract
    results = await asyncio.gather(*(client.post('/claim', json=claim()) for _ in range(5)))
    assert all(r.status_code == 200 and r.json()['scan_sequence'] == 1 for r in results)
    assert (await client.post('/recover', json=recovery())).status_code == 200
    assert (await client.post('/recover', json={**recovery(), 'recovery_credential_hash':'d'*64})).status_code == 403
    assert (await client.post('/claim', json={**claim(), 'recovery_credential_hash':'d'*64})).status_code == 403
    async with sessions() as db:
        assert (await db.get(Queue, 'queue')).current_sequence == 1


@pytest.mark.parametrize('endpoint', ['/claim', '/register', '/recover'])
async def test_expiry_checked_after_queue_lock(contract, endpoint):
    client, sessions, engine = contract
    if endpoint != '/claim':
        await client.post('/claim', json=claim())
    # Observe a blocked backend, then move the deadline into the past under the
    # lock. A stale pre-lock deadline check would incorrectly admit the request.
    async with sessions() as blocker:
        await blocker.execute(select(Queue).where(Queue.id=='queue').with_for_update())
        task = asyncio.create_task(client.post(endpoint, json=(claim() if endpoint=='/claim' else registration() if endpoint=='/register' else recovery())))
        try:
            blocked = False
            for _ in range(100):
                async with engine.connect() as observer:
                    blocked = (await observer.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE '%queues%'"))).scalar_one() > 0
                if blocked:
                    break
                await asyncio.sleep(.02)
            assert blocked, 'Request did not reach the database lock'
            token = await blocker.get(Token, 't0')
            token.reservation_expires_at = qm._now()-timedelta(seconds=1)
            await blocker.commit()
            response = await asyncio.wait_for(task, 5)
            assert response.status_code == 410, response.text
        finally:
            await blocker.rollback()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


async def test_registered_recovery_after_expiry_and_private_tracking(contract):
    client, sessions, _ = contract
    await client.post('/claim', json=claim())
    await client.post('/register', json=registration())
    async with sessions.begin() as db:
        token = await db.get(Token, 't0')
        assert token.phone_number == '9876543210' and token.customer_name == 'Manya Kumar'
        token.reservation_expires_at = qm._now()-timedelta(minutes=1)
    assert (await client.post('/recover', json=recovery())).json()['status'] == 'WAITING'
    assert (await client.post('/register', json=registration())).status_code == 200
    assert (await client.get('/token/t0/status', headers={'X-Tracking-Secret':'d'*64})).status_code == 403
    response = await client.get('/token/t0/status', headers={'X-Tracking-Secret':'c'*64})
    assert response.status_code == 200
    assert response.json()['people_ahead'] == 0
    assert 'customer_name' not in response.json() and 'phone_number' not in response.json()
    assert response.headers['cache-control'] == 'no-store'


async def test_reject_and_validation(contract):
    client, _, _ = contract
    assert (await client.post('/claim', json={**claim(), 'display_number':'wrong'})).status_code == 400
    await client.post('/claim', json=claim())
    assert (await client.post('/register', json={**registration(), 'phone_number':'123'})).status_code == 422
    assert (await client.post('/register', json={**registration(), 'customer_name':'   '})).status_code == 422
    assert (await client.post('/reject', json={**recovery(), 'recovery_credential_hash':'d'*64})).status_code == 403
    assert (await client.post('/reject', json=recovery())).json()['status'] == 'CANCELLED'
    assert (await client.post('/reject', json=recovery())).status_code == 200
    assert (await client.post('/register', json=registration())).status_code == 400


async def test_expiry_at_exact_deadline(contract, monkeypatch):
    client, sessions, _ = contract
    await client.post('/claim', json=claim())
    async with sessions() as db:
        deadline = (await db.get(Token, 't0')).reservation_expires_at
    monkeypatch.setattr(qm, '_now', lambda: deadline)
    assert (await client.post('/register', json=registration())).status_code == 410

async def test_competing_browsers_cannot_take_over_claim(contract):
    client, sessions, _ = contract
    first = claim()
    other = {**claim(), 'browser_session_id':'another-browser-000', 'recovery_credential_hash':'d'*64}
    replies = await asyncio.gather(client.post('/claim', json=first), client.post('/claim', json=other))
    assert sorted(r.status_code for r in replies) == [200, 403]
    async with sessions() as db:
        assert (await db.get(Queue, 'queue')).current_sequence == 1


async def test_concurrent_distinct_claims_get_unique_priorities(contract):
    client, _, _ = contract
    replies = await asyncio.gather(*(client.post('/claim', json=claim(n)) for n in range(4)))
    assert all(r.status_code == 200 for r in replies)
    assert sorted(r.json()['scan_sequence'] for r in replies) == [1,2,3,4]


async def test_concurrent_registration_is_one_activation(contract):
    from app.models.schema import EventLog
    from sqlalchemy import func
    client, sessions, _ = contract
    await client.post('/claim', json=claim())
    replies = await asyncio.gather(*(client.post('/register', json=registration()) for _ in range(4)))
    assert all(r.status_code == 200 and r.json()['scan_sequence'] == 1 for r in replies)
    async with sessions() as db:
        assert (await db.execute(select(func.count()).select_from(EventLog).where(EventLog.event_type=='WAITING'))).scalar_one() == 1
        assert (await db.get(Queue, 'queue')).current_sequence == 1


async def test_live_status_uses_backend_queue_and_counter(contract):
    client, sessions, _ = contract
    for n in (0,1):
        await client.post('/claim', json=claim(n))
        await client.post('/register', json=registration(n))
    async with sessions.begin() as db:
        counter = await db.get(Counter, 'counter')
        await qm._call_next_waiting(db, counter, 'staff', qm._now())
    waiting = (await client.get('/token/t1/status', headers={'X-Tracking-Secret':'c'*64})).json()
    assert waiting['people_ahead'] == 1 and waiting['estimated_wait_minutes'] == 5
    called = (await client.get('/token/t0/status', headers={'X-Tracking-Secret':'c'*64})).json()
    assert called['counter_label'] == 'Counter 1' and called['people_ahead'] is None
    async with sessions.begin() as db:
        counter = await db.get(Counter, 'counter')
        counter.status = 'PAUSED'
    paused = (await client.get('/token/t1/status', headers={'X-Tracking-Secret':'c'*64})).json()
    assert paused['estimated_wait_minutes'] is None
