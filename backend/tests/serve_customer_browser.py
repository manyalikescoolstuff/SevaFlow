"""Disposable PostgreSQL + real API for manual browser verification.

Run from backend: venv/Scripts/python.exe -B -m tests.serve_customer_browser
The schema is created on startup and removed on graceful shutdown. No public
queue, token, staff or personal data is read or modified.
"""
import hashlib
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta
import uvicorn
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.schema import Service, Queue, Counter, Token
from app.api.customer import router
from app.services.queue_manager import _now

schema = 'test_customer_browser_' + uuid.uuid4().hex
engine = create_async_engine(settings.DATABASE_URL, connect_args={'server_settings': {'search_path': schema}})
sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

@asynccontextmanager
async def lifespan(app):
    admin = create_async_engine(settings.DATABASE_URL)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions.begin() as db:
            db.add(Service(id='svc-aadhaar', name='Aadhaar test service', expected_duration_sec=300))
            await db.flush()
            db.add(Queue(id='test-queue', service_id='svc-aadhaar', current_sequence=0))
            await db.flush()
            db.add(Counter(id='test-counter', label='Test counter', service_id='svc-aadhaar', queue_id='test-queue'))
            for n in (24,25):
                db.add(Token(id=f'browser-token-{n}', display_number=f'A0{n}', queue_id='test-queue', status='RESERVED',
                    hardware_reservation_id=f'browser-check-{n}', claim_secret_hash=hashlib.sha256(b'browser-test-only').hexdigest(),
                    reservation_expires_at=_now()+timedelta(minutes=15)))
        print('Isolated browser test API ready. No public queue data is used.')
        yield
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()

app = FastAPI(lifespan=lifespan)
app.include_router(router, prefix='/api/v1')
async def database():
    async with sessions() as db:
        try:
            yield db
        finally:
            await db.rollback()
app.dependency_overrides[get_db] = database

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8001)
