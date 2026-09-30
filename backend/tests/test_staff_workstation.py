"""Real login, ownership, stale-state and retry tests for the live workstation."""
import asyncio
import uuid
import httpx
import pytest_asyncio
from fastapi import FastAPI
from app.api.staff import router as staff_router
from app.api.workstation import router as workstation_router
from app.api.customer import router as customer_router
from app.api.admin import router as admin_router
from app.core.database import get_db
from app.core.security import hash_password
from app.models.schema import Staff, Counter, Token
from tests.test_customer_contract import contract, claim, registration


@pytest_asyncio.fixture
async def live(contract):
    _, sessions, _ = contract
    async with sessions.begin() as db:
        password = hash_password('test-password')
        db.add_all([
            Staff(id='operator', name='Test Operator', username='operator', hashed_password=password, role='STAFF'),
            Staff(id='other', name='Other Operator', username='other', hashed_password=password, role='STAFF'),
            Staff(id='admin', name='Administrator', username='admin', hashed_password=password, role='ADMIN'),
        ])
        await db.flush()
        counter = await db.get(Counter, 'counter')
        counter.staff_id = 'operator'
        db.add(Counter(id='other-counter', label='Counter 2', service_id='service', queue_id='queue', staff_id='other'))
    app = FastAPI()
    for router in (staff_router, workstation_router, customer_router, admin_router):
        app.include_router(router, prefix='/api/v1')
    async def database():
        async with sessions() as db:
            try:
                yield db
            finally:
                await db.rollback()
    app.dependency_overrides[get_db] = database
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test/api/v1/') as client:
        login = await client.post('auth/login', data={'username':'operator','password':'test-password'})
        assert login.status_code == 200, login.text
        client.headers['Authorization'] = 'Bearer ' + login.json()['access_token']
        yield client, sessions


def command(token_id=None, status=None, request_id=None):
    return {'request_id':request_id or str(uuid.uuid4()), 'expected_token_id':token_id, 'expected_token_status':status}


async def register(client, n=0):
    assert (await client.post('customer/claim', json=claim(n))).status_code == 200
    assert (await client.post('customer/register', json=registration(n))).status_code == 200


async def test_full_staff_customer_flow_and_lost_response_retry(live):
    client, _ = live
    await register(client)
    await register(client, 1)
    snapshot = (await client.get('staff/workstation')).json()
    assert snapshot['waiting_count'] == 2
    assert snapshot['counter']['id'] == 'counter'
    next_req = command()
    first = await client.post('staff/counters/counter/next', json=next_req)
    assert first.status_code == 200 and first.json()['current_token_id'] == 't0'
    tracking = (await client.get('customer/token/t0/status', headers={'X-Tracking-Secret':'c'*64})).json()
    assert tracking['status'] == 'CALLED' and tracking['counter_label'] == 'Counter 1'
    start_req = command('t0','CALLED')
    assert (await client.post('staff/counters/counter/start', json=start_req)).status_code == 200
    completion = await client.post('staff/counters/counter/next', json=command('t0','SERVING'))
    assert completion.json()['current_token_id'] == 't1'
    assert (await client.post('staff/counters/counter/next', json=next_req)).json() == first.json()
    assert (await client.post('staff/counters/counter/start', json=start_req)).status_code == 200
    snapshot = (await client.get('staff/workstation')).json()
    assert snapshot['current_token']['id'] == 't1' and snapshot['current_token']['status'] == 'CALLED'
    assert snapshot['counter']['served_today'] == 1
    tracking = (await client.get('customer/token/t0/status', headers={'X-Tracking-Secret':'c'*64})).json()
    assert tracking['status'] == 'COMPLETED'


async def test_concurrent_duplicate_and_stale_commands(live):
    client, _ = live
    await register(client)
    payload = command()
    results = await asyncio.gather(*(client.post('staff/counters/counter/next', json=payload) for _ in range(4)))
    assert all(r.status_code == 200 and r.json() == results[0].json() for r in results)
    assert (await client.post('staff/counters/counter/next', json=command())).status_code == 409
    assert (await client.post('staff/counters/counter/start', json=payload)).status_code == 409
    assert (await client.get('staff/workstation')).json()['counter']['served_today'] == 0


async def test_pause_preserves_service_and_stops_dispatch(live):
    client, _ = live
    await register(client)
    await register(client,1)
    await client.post('staff/counters/counter/next', json=command())
    await client.post('staff/counters/counter/start', json=command('t0','CALLED'))
    assert (await client.post('staff/counters/counter/pause', json=command('t0','SERVING'))).status_code == 200
    snapshot = (await client.get('staff/workstation')).json()
    assert snapshot['current_token']['status'] == 'SERVING'
    assert (await client.post('staff/counters/counter/next', json=command('t0','SERVING'))).json()['current_token_id'] is None
    assert (await client.post('staff/counters/counter/next', json=command())).status_code == 409
    await client.post('staff/counters/counter/resume', json=command())
    assert (await client.post('staff/counters/counter/next', json=command())).json()['current_token_id'] == 't1'


async def test_counter_ownership_login_and_admin_monitor_only(live):
    client, sessions = live
    assert (await client.post('staff/counters/other-counter/next', json=command())).status_code == 403
    assert (await client.post('counters/other-counter/next')).status_code == 403
    assert (await client.post('auth/login', data={'username':'operator','password':'wrong'})).status_code == 401
    admin = (await client.post('auth/login', data={'username':'admin','password':'test-password'})).json()
    headers = {'Authorization':'Bearer '+admin['access_token']}
    assert (await client.get('staff/workstation', headers=headers)).status_code == 403
    assert (await client.post('staff/counters/counter/next', json=command(), headers=headers)).status_code == 403
    async with sessions.begin() as db:
        (await db.get(Staff,'operator')).is_active = False
    assert (await client.get('staff/workstation')).status_code == 401


async def test_unregistered_tokens_ineligible_and_counter_closed(live):
    client, sessions = live
    await client.post('customer/claim', json=claim())
    response = await client.post('staff/counters/counter/next', json=command())
    assert response.status_code == 200 and response.json()['current_token_id'] is None
    async with sessions.begin() as db:
        assert (await db.get(Token,'t0')).status == 'CLAIMED'
        (await db.get(Counter,'counter')).status = 'CLOSED'
    assert (await client.post('staff/counters/counter/resume', json=command())).status_code == 409


async def test_unassigned_operator_and_cache_headers(live):
    client, sessions = live
    async with sessions.begin() as db:
        (await db.get(Counter,'counter')).staff_id = None
    response = await client.get('staff/workstation')
    assert response.json()['counter'] is None
    assert response.headers['cache-control'] == 'no-store'
    assert (await client.post('staff/counters/counter/next', json=command())).status_code == 403


async def act(client, action, token=None, status=None, attempts=None, request_id=None):
    payload = command(token, status, request_id)
    if attempts is not None:
        payload['expected_recall_attempts'] = attempts
    response = await client.post('staff/counters/counter/' + action, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


async def test_two_recalls_require_two_actual_completions_and_retries_are_safe(live):
    client, sessions = live
    for n in range(3):
        await register(client, n)
    await act(client, 'next')
    missed_id = str(uuid.uuid4())
    first = await act(client, 'missed', 't0', 'CALLED', request_id=missed_id)
    assert first['current_token_id'] == 't1'
    assert await act(client, 'missed', 't0', 'CALLED', request_id=missed_id) == first
    async with sessions() as db:
        token = await db.get(Token, 't0')
        assert (token.status, token.recall_attempts, token.recall_ready) == ('MISSED', 0, False)
        priority = token.scan_sequence
        missed_at = token.missed_at
    assert (await client.post('staff/counters/counter/next', json=command('t1', 'CALLED'))).status_code == 409
    await act(client, 'start', 't1', 'CALLED')
    assert (await client.post('staff/counters/counter/missed', json=command('t1', 'SERVING'))).status_code == 409
    assert (await act(client, 'next', 't1', 'SERVING'))['current_token_id'] == 't0'
    assert (await client.post('staff/counters/counter/missed', json=command('t0', 'CALLED'))).status_code == 409
    absent_id = str(uuid.uuid4())
    responses = await asyncio.gather(*(act(client, 'absent-again', 't0', 'CALLED', 0, absent_id) for _ in range(3)))
    assert all(r == responses[0] for r in responses)
    assert responses[0]['current_token_id'] == 't2'
    async with sessions() as db:
        token = await db.get(Token, 't0')
        assert (token.status, token.recall_attempts, token.recall_ready) == ('MISSED', 1, False)
        assert token.missed_at == missed_at and token.scan_sequence == priority
    await act(client, 'start', 't2', 'CALLED')
    assert (await act(client, 'next', 't2', 'SERVING'))['current_token_id'] == 't0'
    stale = {**command('t0','CALLED'), 'expected_recall_attempts':0}
    assert (await client.post('staff/counters/counter/absent-again', json=stale)).status_code == 409
    assert await act(client, 'absent-again', 't0', 'CALLED', 0, absent_id) == responses[0]
    assert (await act(client, 'absent-again', 't0', 'CALLED', 1))['current_token_id'] is None
    async with sessions() as db:
        token = await db.get(Token, 't0')
        assert token.status == 'CLOSED_MISSED' and token.recall_attempts == 2
        assert token.completed_at is None and token.scan_sequence == priority
        assert (await db.get(Counter, 'counter')).served_today == 2
    tracking = (await client.get('customer/token/t0/status', headers={'X-Tracking-Secret':'c'*64})).json()
    assert tracking['status'] == 'CLOSED_MISSED'


async def test_empty_counter_cannot_create_recall_and_pause_preserves_eligibility(live):
    client, sessions = live
    await register(client)
    await act(client, 'next')
    await act(client, 'missed', 't0', 'CALLED')
    for _ in range(2):
        assert (await act(client, 'next'))['current_token_id'] is None
    async with sessions() as db:
        token = await db.get(Token, 't0')
        assert token.status == 'MISSED' and token.recall_attempts == 0
    await register(client, 1)
    assert (await act(client, 'next'))['current_token_id'] == 't1'
    await act(client, 'start', 't1', 'CALLED')
    await act(client, 'pause', 't1', 'SERVING')
    assert (await act(client, 'next', 't1', 'SERVING'))['current_token_id'] is None
    async with sessions() as db:
        assert (await db.get(Token, 't0')).recall_ready is True
    await act(client, 'resume')
    assert (await act(client, 'next'))['current_token_id'] == 't0'
    await act(client, 'start', 't0', 'CALLED')
    await act(client, 'next', 't0', 'SERVING')
    async with sessions() as db:
        token = await db.get(Token, 't0')
        assert token.status == 'COMPLETED' and token.recall_attempts == 0
        assert token.serving_started_at is not None


async def test_missed_actions_are_owned_retry_safe_and_pause_does_not_dispatch(live):
    client, sessions = live
    await register(client)
    await register(client, 1)
    await act(client, 'next')
    assert (await client.post('staff/counters/counter/absent-again', json={**command('t0','CALLED'), 'expected_recall_attempts':0})).status_code == 409
    assert (await client.post('staff/counters/other-counter/missed', json=command('t0','CALLED'))).status_code == 403
    await act(client, 'pause', 't0', 'CALLED')
    payload = command('t0', 'CALLED')
    result = await client.post('counters/counter/missed', json=payload)
    assert result.status_code == 200 and result.json()['current_token_id'] is None
    assert (await client.post('staff/counters/counter/missed', json=payload)).json() == result.json()
    assert (await client.post('counters/counter/missed')).status_code == 422
    snapshot = (await client.get('staff/workstation')).json()
    assert [t['id'] for t in snapshot['missed']] == ['t0']
    assert snapshot['waiting_count'] == 1
    async with sessions() as db:
        assert (await db.get(Token, 't0')).recall_attempts == 0
        assert (await db.get(Token, 't1')).status == 'WAITING'
    await act(client, 'resume')
    assert (await act(client, 'next'))['current_token_id'] == 't1'


async def test_second_missed_token_is_not_silently_scheduled(live):
    client, sessions = live
    await register(client)
    await register(client, 1)
    await act(client, 'next')
    await act(client, 'missed', 't0', 'CALLED')
    result = await client.post('staff/counters/counter/missed', json=command('t1','CALLED'))
    assert result.status_code == 409
    assert 'Multiple-missed' in result.json()['detail']
    async with sessions() as db:
        assert (await db.get(Token, 't1')).status == 'CALLED'
        assert (await db.get(Counter, 'counter')).current_token_id == 't1'
        assert (await db.get(Token, 't0')).recall_attempts == 0
