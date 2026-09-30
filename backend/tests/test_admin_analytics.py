"""Historical analytics cohorts, timezone boundaries and missing measurements."""
from datetime import datetime, timedelta, timezone
from tests.test_customer_contract import contract
from tests.test_staff_workstation import live
from tests.test_admin_monitor import admin_headers
from app.models.schema import Token

DAY = datetime(2026, 1, 2, tzinfo=timezone(timedelta(hours=5, minutes=30)))


async def test_analytics_auth_validation_and_empty_day(live):
    client, _ = live
    assert (await client.get('admin/analytics')).status_code == 403
    assert (await client.get('admin/analytics', headers={'Authorization':''})).status_code == 401
    headers = await admin_headers(client)
    for date in ('invalid', '2026-02-30', '9999-12-31'):
        assert (await client.get('admin/analytics', params={'date':date}, headers=headers)).status_code == 422
    response = await client.get('admin/analytics?date=2020-01-01', headers=headers)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    data = response.json()
    assert len(data['hourly']) == 24 and data['partial_day'] is False
    assert data['summary']['registrations'] == 0
    assert data['summary']['avg_wait_seconds'] is None
    assert data['utilization_percent'] is None


async def test_analytics_midnight_cross_day_cohorts_and_exact_averages(live):
    client, sessions = live
    async with sessions.begin() as db:
        first = await db.get(Token, 't0')
        first.status = 'COMPLETED'
        first.registered_at = DAY - timedelta(minutes=5)
        first.serving_started_at = DAY - timedelta(minutes=1)
        first.completed_at = DAY  # Included in completion cohort, previous day's registration.
        second = await db.get(Token, 't1')
        second.status = 'COMPLETED'
        second.registered_at = DAY
        second.serving_started_at = DAY + timedelta(minutes=10)
        second.completed_at = DAY + timedelta(minutes=13)
        third = await db.get(Token, 't2')
        third.status = 'CLOSED_MISSED'
        third.registered_at = DAY + timedelta(hours=1)
        third.completed_at = DAY + timedelta(hours=1, minutes=5)  # Legacy closure is not service.
        fourth = await db.get(Token, 't3')
        fourth.status = 'COMPLETED'
        fourth.registered_at = DAY + timedelta(days=1)
        fourth.serving_started_at = DAY + timedelta(days=1)
        fourth.completed_at = DAY + timedelta(days=1)  # Exclusive upper bound.
    data = (await client.get('admin/analytics?date=2026-01-02', headers=await admin_headers(client))).json()
    assert data['summary'] == {'registrations':2, 'completions':2, 'avg_wait_seconds':420.0,
        'wait_samples':2, 'avg_service_seconds':120.0, 'service_samples':2}
    assert data['hourly'][0]['registrations'] == 1 and data['hourly'][0]['completions'] == 2
    assert data['hourly'][1]['registrations'] == 1 and data['hourly'][1]['avg_wait_seconds'] is None
    assert data['services'][0]['completions'] == 2
    assert 'customer_name' not in str(data) and 'claim_secret' not in str(data)


async def test_analytics_missing_invalid_and_zero_duration_samples(live):
    client, sessions = live
    async with sessions.begin() as db:
        for n in range(3):
            token = await db.get(Token, f't{n}')
            token.status = 'COMPLETED'
            token.registered_at = DAY
            token.completed_at = DAY + timedelta(hours=1)
        (await db.get(Token, 't0')).serving_started_at = None
        (await db.get(Token, 't1')).serving_started_at = DAY + timedelta(hours=2)
        last = await db.get(Token, 't2')
        last.registered_at = DAY + timedelta(hours=1)
        last.serving_started_at = last.completed_at
    data = (await client.get('admin/analytics?date=2026-01-02', headers=await admin_headers(client))).json()
    assert data['summary']['completions'] == 3
    assert data['summary']['wait_samples'] == data['summary']['service_samples'] == 1
    assert data['summary']['avg_wait_seconds'] == data['summary']['avg_service_seconds'] == 0
