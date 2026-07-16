from datetime import datetime, timezone

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.exceptions import AuthException, ForbiddenException, PaymentRequiredException
from core.security import decode_token
from models import Subscription, User


async def _check_subscription_expiry(user: User, db: AsyncSession) -> None:
    if not user.is_premium:
        return
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.user_id == user.id,
            Subscription.is_active == True,
        )
        .order_by(Subscription.ends_at.desc())
    )
    active_sub = result.scalars().first()
    if active_sub and active_sub.ends_at and active_sub.ends_at < datetime.now(timezone.utc):
        active_sub.is_active = False
        user.is_premium = False


async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise AuthException("Invalid authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise AuthException("Empty token")
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise AuthException("Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise AuthException("Invalid token payload")
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise AuthException("Invalid token payload")
    result = await db.execute(select(User).where(User.id == user_id_int))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthException("User not found or inactive")
    user.last_active = datetime.now(timezone.utc)
    await _check_subscription_expiry(user, db)
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    admin_phones = settings.admin_phones_list
    if not admin_phones:
        raise ForbiddenException("No admin accounts configured")
    if user.phone_number not in admin_phones:
        raise ForbiddenException("Admin access required")
    return user


async def get_premium_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_premium:
        raise PaymentRequiredException()
    return user
