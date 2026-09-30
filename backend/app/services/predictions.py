"""Transparent recorded-day demand baseline; no trained model or queue mutation."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

CENTRE_TIMEZONE = timezone(timedelta(hours=5, minutes=30))
LOOKBACK_DAYS = 28
MIN_RECORDED_DAYS = 7
MAX_HISTORY_AGE_DAYS = 7


def build_forecast(rows, services, now):
    """Rows are (local calendar date, hour, service ID, registration count)."""
    today = now.astimezone(CENTRE_TIMEZONE).date()
    first = today - timedelta(days=LOOKBACK_DAYS)
    daily = defaultdict(int)
    hours = defaultdict(int)
    demand = defaultdict(int)
    service_days = defaultdict(set)
    for day, hour, sid, count in rows:
        if first <= day < today and count > 0:
            daily[day] += count
            hours[hour] += count
            demand[sid] += count
            service_days[sid].add(day)
    days = len(daily)
    latest = max(daily) if daily else None
    ready = days >= MIN_RECORDED_DAYS and latest is not None and (today - latest).days <= MAX_HISTORY_AGE_DAYS
    reason = None
    if days < MIN_RECORDED_DAYS:
        reason = f'At least {MIN_RECORDED_DAYS} prior days with registrations are required; {days} available.'
    elif (today - latest).days > MAX_HISTORY_AGE_DAYS:
        reason = 'The latest recorded activity is more than seven days old.'
    return {
        'forecast_date': (today + timedelta(days=1)).isoformat(), 'timezone': 'Asia/Kolkata',
        'generated_at': now, 'status': 'available' if ready else 'insufficient_data', 'reason': reason,
        'method': 'Mean registrations per recorded day; provisional planning baseline, not a validated prediction.',
        'window_start': first.isoformat(), 'window_end': (today - timedelta(days=1)).isoformat(),
        'recorded_days': days, 'required_days': MIN_RECORDED_DAYS,
        'days_without_records': LOOKBACK_DAYS - days,
        'latest_recorded_date': latest.isoformat() if latest else None,
        'registration_samples': sum(daily.values()),
        'expected_registrations': round(sum(daily.values()) / days, 1) if ready else None,
        'historical_daily_min': min(daily.values()) if daily else None,
        'historical_daily_max': max(daily.values()) if daily else None,
        'hourly': [{'hour': hour, 'expected_registrations': round(hours[hour] / days, 1)} for hour in range(24)] if ready else [],
        'services': [{'service_id': sid, 'service_name': name, 'recorded_days': len(service_days[sid]),
            'expected_registrations': round(demand[sid] / days, 1) if ready and len(service_days[sid]) >= 3 else None}
            for sid, name in services],
        'expected_wait_minutes': None,
        'limitations': [
            'Days without registrations are excluded: closures and missing collection cannot be distinguished from zero demand. This may bias the baseline upward.',
            'Assumes tomorrow resembles the recorded days. Weekdays, holidays and seasonal changes are not modeled.',
            'Historical minimum and maximum are observed values, not a forecast confidence interval.',
            'Service estimates need activity on at least three recorded days. Missing service estimates mean service totals may not match the centre total.',
            'Future wait and queue pressure are unavailable without planned staffing, opening hours and validated arrival modeling.',
        ],
    }
