"""
Security utilities: password hashing, JWT tokens, hardware HMAC verification.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
import bcrypt
from app.core.config import settings

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False



# ---------------------------------------------------------------------------
# JWT (staff sessions)
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.STAFF_JWT_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.STAFF_JWT_SECRET, algorithm=settings.STAFF_JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.STAFF_JWT_SECRET, algorithms=[settings.STAFF_JWT_ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# SHA-256 helpers (claim secret, recovery credential, tracking secret)
# ---------------------------------------------------------------------------

def sha256_hex(value: str) -> str:
    """Return the lowercase hex SHA-256 hash of value."""
    return hashlib.sha256(value.encode()).hexdigest()


def generate_secret() -> str:
    """Generate a URL-safe 32-byte random token."""
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# Hardware HMAC verification (Pico W shared secret)
# ---------------------------------------------------------------------------

def verify_hardware_hmac(payload: str, signature: str) -> bool:
    """
    Verify HMAC-SHA256 signature from Pico W.
    payload: the raw request body string
    signature: hex-encoded HMAC from X-Pico-Signature header
    """
    expected = hmac.new(
        settings.HARDWARE_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
