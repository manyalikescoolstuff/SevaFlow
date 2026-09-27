"""
Staff authentication dependency for FastAPI endpoints.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.schema import Staff

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
