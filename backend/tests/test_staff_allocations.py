import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from tests.test_customer_contract import contract
from tests.test_staff_workstation import live, register, act
from tests.test_admin_monitor import admin_headers
from app.models.schema import Counter

def allocation(**changes):
    now = datetime.now(timezone.utc)
    return dict(id=str(uuid.uuid4()), staff_id='operator', counter_id='other-counter',
        starts_at=(now-timedelta(minutes=1)).isoformat(), ends_at=(now+timedelta(hours=1)).isoformat(), **changes)

async def test_authority_overlap_and_retry(live):
    client, _ = live
    req = allocation()
    assert (await client.post('admin/allocations', json=req)).status_code == 403
    headers = await admin_headers(client)
    results = await asyncio.gather(*[client.post('admin/allocations', json=req, headers=headers) for _ in range(2)])
    assert [r.status_code for r in results] == [200, 200]
    conflict = {**req, 'id': str(uuid.uuid4())}
    assert (await client.post('admin/allocations', json=conflict, headers=headers)).status_code == 409
    changed = {**req, 'counter_id': 'counter'}
    assert (await client.post('admin/allocations', json=changed, headers=headers)).status_code == 409
    assert (await client.post(f"admin/allocations/{req['id']}/cancel", headers=headers)).status_code == 200
    assert (await client.post('admin/allocations', json=conflict, headers=headers)).status_code == 200

async def test_free_handover_restores_and_changes_permissions(live):
    client, sessions = live
    headers = await admin_headers(client)
    req = allocation()
    assert (await client.post('admin/allocations', json=req, headers=headers)).status_code == 200
    endpoint = f"admin/allocations/{req['id']}"
    for _ in range(2):
        assert (await client.post(endpoint+'/apply', headers=headers)).status_code == 200
    state = (await client.get('staff/workstation')).json()
    assert state['counter']['id'] == 'other-counter'
    assert (await act(client, 'next')).status_code == 403
    for _ in range(2):
        assert (await client.post(endpoint+'/release', headers=headers)).status_code == 200
    async with sessions() as db:
        assert (await db.get(Counter, 'counter')).staff_id == 'operator'
        assert (await db.get(Counter, 'other-counter')).staff_id == 'other'

async def test_busy_and_outside_slot_are_blocked(live):
    client, _ = live
    headers = await admin_headers(client)
    req = allocation()
    await client.post('admin/allocations', json=req, headers=headers)
    await register(client)
    await act(client, 'next')
    assert (await client.post(f"admin/allocations/{req['id']}/apply", headers=headers)).status_code == 409
    assert (await client.post('admin/allocations', json={**req, 'id': str(uuid.uuid4()), 'ends_at':req['starts_at']}, headers=headers)).status_code == 422

async def test_concurrent_overlapping_bookings_only_one_wins(live):
    client, _ = live
    headers = await admin_headers(client)
    results = await asyncio.gather(*[client.post('admin/allocations', json=allocation(), headers=headers) for _ in range(2)])
    assert sorted(r.status_code for r in results) == [200, 409]
