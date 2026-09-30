"""Admin monitoring uses persisted data and enforces read-only admin access."""
from datetime import datetime, timedelta, timezone
from tests.test_staff_workstation import live, register, act, command
from tests.test_customer_contract import contract
from app.models.schema import Counter, Token, Staff


async def admin_headers(client):
    response = await client.post('auth/login', data={'username':'admin','password':'test-password'})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


async def test_admin_role_required_and_no_mutation_access(live):
    client, sessions = live
    assert (await client.get('admin/monitor', headers={'Authorization':''})).status_code == 401
    assert (await client.get('admin/monitor')).status_code == 403
    headers = await admin_headers(client)
    response = await client.get('admin/monitor', headers=headers)
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert (await client.post('staff/counters/counter/next', json=command(), headers=headers)).status_code == 403
    async with sessions.begin() as db:
        (await db.get(Staff, 'admin')).is_active = False
    assert (await client.get('admin/monitor', headers=headers)).status_code == 401


async def test_admin_snapshot_tracks_real_staff_changes_without_customer_details(live):
    client, sessions = live
    headers = await admin_headers(client)
    await register(client)
    await register(client, 1)
    data = (await client.get('admin/monitor', headers=headers)).json()
    assert data['waiting_now'] == 2 and data['registered_today'] == 2
    assert [t['id'] for t in data['queues'][0]['upcoming']] == ['t0','t1']
    await act(client, 'next')
    data = (await client.get('admin/monitor', headers=headers)).json()
    assert data['queues'][0]['called'] == 1 and data['queues'][0]['serving'] == 0
    await act(client, 'start', 't0', 'CALLED')
    await act(client, 'next', 't0', 'SERVING')
    await act(client, 'missed', 't1', 'CALLED')
    data = (await client.get('admin/monitor', headers=headers)).json()
    assert data['completed_today'] == 1 and data['waiting_now'] == 0
    assert data['queues'][0]['missed'] == 1
    for value in ('phone_number', 'customer_name', 'hashed_password', 'tracking_secret', 'recovery_credential', '9876543210', 'Manya Kumar'):
        assert value not in str(data)
    async with sessions() as db:
        assert (await db.get(Token, 't1')).status == 'MISSED'


async def test_unavailable_wait_closed_counter_and_india_day_boundary(live):
    client, sessions = live
    headers = await admin_headers(client)
    await register(client)
    zone = timezone(timedelta(hours=5, minutes=30))
    midnight = datetime.now(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    async with sessions.begin() as db:
        (await db.get(Token, 't0')).registered_at = midnight - timedelta(seconds=1)
        (await db.get(Counter, 'counter')).status = 'CLOSED'
        (await db.get(Counter, 'other-counter')).status = 'PAUSED'
        (await db.get(Counter, 'counter')).served_today = 999
    data = (await client.get('admin/monitor', headers=headers)).json()
    assert data['registered_today'] == 0 and data['completed_today'] == 0
    assert data['waiting_now'] == 1 and data['active_counters'] == 0
    assert data['queues'][0]['estimated_wait_minutes'] is None
    assert {c['status'] for c in data['counters']} == {'CLOSED','PAUSED'}
    assert data['report_date'] == midnight.date().isoformat()
