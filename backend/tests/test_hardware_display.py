import pytest
from fastapi import FastAPI
import httpx
from app.api.hardware import router
from app.core.database import get_db
from app.core.config import settings
from app.models.schema import Counter, Token
from tests.test_customer_contract import contract

@pytest.mark.asyncio
async def test_display_auth_and_counter_states(contract):
    _, sessions, _ = contract
    app = FastAPI()
    app.include_router(router)
    async def database():
        async with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = database
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        path = '/hardware/counters/counter/display'
        assert (await client.get(path)).status_code == 422
        assert (await client.get(path, headers={'X-Hardware-Secret': 'wrong'})).status_code == 401
        client.headers['X-Hardware-Secret'] = settings.HARDWARE_SECRET
        assert (await client.get('/hardware/counters/missing/display')).status_code == 404
        assert (await client.get(path)).json()['display_number'] is None
        for state in ('RESERVED', 'WAITING', 'CALLED', 'SERVING', 'MISSED', 'COMPLETED', 'CLOSED_MISSED'):
            async with sessions.begin() as db:
                (await db.get(Counter, 'counter')).current_token_id = 't0'
                (await db.get(Token, 't0')).status = state
            response = await client.get(path)
            assert response.status_code == 200
            assert response.headers['cache-control'] == 'no-store'
            data = response.json()
            assert set(data) == {'counter_id', 'display_number', 'token_status'}
            assert data['display_number'] == ('A024' if state in ('CALLED', 'SERVING') else None)
        async with sessions.begin() as db:
            (await db.get(Token, 't0')).status = 'SERVING'
            (await db.get(Counter, 'counter')).status = 'PAUSED'
        assert (await client.get(path)).json()['display_number'] == 'A024'
        async with sessions.begin() as db:
            (await db.get(Counter, 'counter')).status = 'CLOSED'
        assert (await client.get(path)).json()['display_number'] is None
