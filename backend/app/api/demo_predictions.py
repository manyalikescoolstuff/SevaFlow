from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response
from app.core.deps import require_admin
from app.core.config import settings
from app.services.predictions import build_forecast

router = APIRouter(prefix='/demo-predictions', dependencies=[Depends(require_admin)])

def seed_demo_prediction_data():
    now = datetime.now(timezone.utc)
    # CENTRE_TIMEZONE is Asia/Kolkata
    tz = timezone(timedelta(hours=5, minutes=30))
    today = now.astimezone(tz).date()
    
    # Create fake services
    services = [
        ("svc_demo_1", "General Service (Demo)"),
        ("svc_demo_2", "Fast Track (Demo)")
    ]
    
    # Create fake rows (day, hour, sid, count)
    rows = []
    # Let's populate 14 days of data to make it 'available'
    for i in range(1, 15):
        day = today - timedelta(days=i)
        # some random-ish distribution
        for h in range(9, 17):
            count = 10 + (h % 3) * 5
            rows.append((day, h, "svc_demo_1", count))
            if h % 2 == 0:
                rows.append((day, h, "svc_demo_2", count // 2))
    
    return rows, services

@router.get('')
async def demo_predictions(response: Response):
    if not getattr(settings, 'ENABLE_DEMO_MODE', False):
        raise HTTPException(404, 'Demo mode is disabled')
    response.headers['Cache-Control'] = 'no-store'
    now = datetime.now(timezone.utc)
    rows, services = seed_demo_prediction_data()
    
    return build_forecast(rows, services, now)
