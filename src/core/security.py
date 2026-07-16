from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def generate_otp() -> str:
    import secrets

    return "".join(str(secrets.randbelow(10)) for _ in range(settings.OTP_LENGTH))


async def store_otp_async(phone: str, otp: str, db: AsyncSession) -> None:
    from models import OtpRecord

    await db.execute(delete(OtpRecord).where(OtpRecord.phone == phone))
    db.add(
        OtpRecord(
            phone=phone,
            otp=otp,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_EXPIRE_SECONDS),
        )
    )


async def verify_otp_async(phone: str, otp: str, db: AsyncSession) -> bool:
    from models import OtpRecord

    bypass = settings.OTP_BYPASS.strip()
    if bypass and otp == bypass:
        return True

    result = await db.execute(select(OtpRecord).where(OtpRecord.phone == phone))
    record = result.scalar_one_or_none()
    if not record:
        return False
    if datetime.now(timezone.utc) > record.expires_at:
        await db.execute(delete(OtpRecord).where(OtpRecord.id == record.id))
        return False
    if record.otp != otp:
        return False
    await db.execute(delete(OtpRecord).where(OtpRecord.id == record.id))
    return True


async def check_otp_rate_limit_async(phone: str, db: AsyncSession) -> tuple[bool, int]:
    from models import OtpRecord

    now = datetime.now(timezone.utc)
    window = timedelta(minutes=settings.OTP_RATE_WINDOW_MINUTES)

    result = await db.execute(
        select(OtpRecord).where(
            OtpRecord.phone == phone,
            OtpRecord.created_at >= now - window,
        )
    )
    count = len(result.scalars().all())
    if count >= settings.OTP_RATE_LIMIT:
        oldest_result = await db.execute(
            select(OtpRecord.created_at)
            .where(OtpRecord.phone == phone)
            .order_by(OtpRecord.created_at.asc())
            .limit(1)
        )
        oldest = oldest_result.scalar()
        if oldest:
            retry_after = int(
                (oldest.replace(tzinfo=timezone.utc) + window - now).total_seconds()
            )
            return False, max(retry_after, 0)
        return False, 60
    return True, 0
