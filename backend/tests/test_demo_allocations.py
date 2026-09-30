import pytest
from datetime import datetime, timedelta, timezone
import uuid
from tests.test_customer_contract import contract
from tests.test_staff_workstation import live, register, act
from tests.test_admin_monitor import admin_headers
from app.core.config import settings

@pytest.fixture(autouse=True)
def enable_demo_mode_for_tests():
    original = settings.ENABLE_DEMO_MODE
    settings.ENABLE_DEMO_MODE = True
    yield
    settings.ENABLE_DEMO_MODE = original

async def test_demo_isolation_does_not_affect_live(live):
    client, sessions = live
    headers = await admin_headers(client)

    # 1. Reset demo state
    await client.post('admin/demo-allocations/reset', headers=headers)
    demo_initial = (await client.get('admin/demo-allocations', headers=headers)).json()
    live_initial = (await client.get('admin/allocations', headers=headers)).json()

    # Create a demo allocation
    demo_req = {
        'id': str(uuid.uuid4()),
        'staff_id': demo_initial['staff'][1]['id'],
        'counter_id': demo_initial['counters'][0]['id'],
        'starts_at': (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        'ends_at': (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    }
    r = await client.post('admin/demo-allocations', json=demo_req, headers=headers)
    assert r.status_code == 200, r.text

    # Live allocations should be unchanged
    live_after_demo_mut = (await client.get('admin/allocations', headers=headers)).json()
    assert len(live_after_demo_mut['allocations']) == len(live_initial['allocations'])
    assert not any(a['id'] == demo_req['id'] for a in live_after_demo_mut['allocations'])

    # 2. A real QR registration appears only in live data
    await register(client)
    live_monitor = (await client.get('admin/monitor', headers=headers)).json()
    assert live_monitor['waiting_now'] > 0

    # 3. Demo activity doesn't affect live monitor/reports
    r = await client.post(f"admin/demo-allocations/dalloc-01/release", headers=headers)
    assert r.status_code == 200, r.text
    
    live_monitor_after = (await client.get('admin/monitor', headers=headers)).json()
    assert live_monitor_after['active_counters'] == live_monitor['active_counters']

    # 5. Demo reset changes only demo storage
    await client.post('admin/demo-allocations/reset', headers=headers)
    demo_after_reset = (await client.get('admin/demo-allocations', headers=headers)).json()
    assert len(demo_after_reset['allocations']) < len(demo_initial['allocations']) + 1
    assert not any(a['id'] == demo_req['id'] for a in demo_after_reset['allocations'])

async def test_demo_mode_disabled(live):
    client, _ = live
    headers = await admin_headers(client)
    settings.ENABLE_DEMO_MODE = False
    
    r = await client.get('admin/demo-allocations', headers=headers)
    assert r.status_code == 404

    demo_req = {
        'id': str(uuid.uuid4()),
        'staff_id': 'staff1',
        'counter_id': 'counter1',
        'starts_at': (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        'ends_at': (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    }
    r = await client.post('admin/demo-allocations', json=demo_req, headers=headers)
    assert r.status_code == 404
