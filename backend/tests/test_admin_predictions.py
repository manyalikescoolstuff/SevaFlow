"""Forecast gating, recorded-day denominator, timezone and admin authorization."""
from datetime import datetime, timedelta
from tests.test_customer_contract import contract
from tests.test_staff_workstation import live
from tests.test_admin_monitor import admin_headers
from app.services.predictions import build_forecast, CENTRE_TIMEZONE
from app.models.schema import Token

NOW = datetime(2026, 2, 1, 10, tzinfo=CENTRE_TIMEZONE)
SERVICES = [('one','First service'), ('two','New service')]


def test_recorded_day_mean_excludes_today_and_outside_window():
    rows = [(NOW.date()-timedelta(days=d), 9, 'one', d) for d in range(1,8)]
    rows.extend([(NOW.date(),9,'one',1000), (NOW.date()-timedelta(days=29),9,'one',1000)])
    data = build_forecast(rows, SERVICES, NOW)
    assert data['status'] == 'available' and data['expected_registrations'] == 4
    assert data['recorded_days'] == 7 and data['days_without_records'] == 21
    assert data['registration_samples'] == 28
    assert data['hourly'][9]['expected_registrations'] == 4
    assert data['hourly'][10]['expected_registrations'] == 0
    assert data['services'][0]['expected_registrations'] == 4
    assert data['services'][1]['expected_registrations'] is None
    assert data['historical_daily_min'] == 1 and data['historical_daily_max'] == 7
    assert data['forecast_date'] == '2026-02-02'


def test_insufficient_days_do_not_fabricate_forecast():
    for rows in ([], [(NOW.date()-timedelta(days=1), 9, 'one', 1000)]):
        data = build_forecast(rows, SERVICES, NOW)
        assert data['status'] == 'insufficient_data'
        assert data['expected_registrations'] is None and data['hourly'] == []
        assert all(s['expected_registrations'] is None for s in data['services'])
        assert data['expected_wait_minutes'] is None


def test_stale_history_does_not_unlock_forecast():
    data = build_forecast([(NOW.date()-timedelta(days=d),9,'one',10) for d in range(8,15)], SERVICES, NOW)
    assert data['recorded_days'] == 7 and data['status'] == 'insufficient_data'
    assert 'seven days old' in data['reason']


async def test_predictions_auth_and_real_registration_history(live):
    client, sessions = live
    assert (await client.get('admin/predictions')).status_code == 403
    assert (await client.get('admin/predictions', headers={'Authorization':''})).status_code == 401
    headers = await admin_headers(client)
    empty = (await client.get('admin/predictions', headers=headers)).json()
    assert empty['status'] == 'insufficient_data' and empty['recorded_days'] == 0
    now = datetime.now(CENTRE_TIMEZONE)
    midnight = now.replace(hour=0,minute=0,second=0,microsecond=0)
    async with sessions.begin() as db:
        for n in range(1,8):
            db.add(Token(id=f'historical-{n}', queue_id='queue', status='WAITING',
                display_number=f'H{n}', hardware_reservation_id=f'history-{n}', claim_secret_hash='a'*64,
                reservation_expires_at=now, registered_at=midnight-timedelta(days=n)+timedelta(minutes=5)))
        (await db.get(Token,'t0')).registered_at = midnight  # Current partial day excluded.
    response = await client.get('admin/predictions', headers=headers)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    data = response.json()
    assert data['status'] == 'available' and data['recorded_days'] == 7
    assert data['registration_samples'] == 7 and data['expected_registrations'] == 1
    assert data['hourly'][0]['expected_registrations'] == 1
    for secret in ('claim_secret_hash','phone_number','customer_name','recovery_credential'):
        assert secret not in str(data)
