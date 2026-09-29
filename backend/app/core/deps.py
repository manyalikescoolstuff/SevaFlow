"""
Staff authentication dependency for FastAPI endpoints.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.schema import Staff, Counter, Queue

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_staff(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    staff_id: str = payload.get("sub")
    if not staff_id:
        raise credentials_exception

    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalars().first()
    if not staff or not staff.is_active:
        raise credentials_exception
    return staff


async def require_admin(staff: Staff = Depends(get_current_staff)) -> Staff:
    if staff.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return staff


async def get_counter_staff(counter_id: str, db: AsyncSession = Depends(get_db),
                            staff: Staff = Depends(get_current_staff)) -> Staff:
    """Apply assignment checks to the pre-existing counter action routes too."""
    queue_id = (await db.execute(select(Counter.queue_id).where(Counter.id == counter_id))).scalar_one_or_none()
    if queue_id is None:
        raise HTTPException(404, 'Counter not found')
    await db.execute(select(Queue).where(Queue.id == queue_id).with_for_update())
    counter = (await db.execute(select(Counter).where(Counter.id == counter_id).with_for_update())).scalar_one()
    if staff.role != 'STAFF' or counter.staff_id != staff.id:
        raise HTTPException(403, 'This counter is not assigned to you')
    if counter.status == 'CLOSED':
        raise HTTPException(409, 'Counter is closed')
    return staff
