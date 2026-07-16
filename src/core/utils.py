from datetime import datetime, timezone

from core.config import settings


def calculate_age(dob_str: str) -> int:
    if not dob_str:
        return 0
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except (ValueError, TypeError):
        return 0


async def get_max_photos_for_user(user_id: int, db) -> int:
    from sqlalchemy import select
    from models import User, Subscription, Plan

    result = await db.execute(
        select(User.is_premium).where(User.id == user_id)
    )
    row = result.first()
    is_premium = row[0] if row else False

    plan = None
    if is_premium:
        result = await db.execute(
            select(Plan).join(Subscription, Subscription.plan_id == Plan.id).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
            ).order_by(Subscription.ends_at.desc())
        )
        plan = result.scalars().first()
    else:
        result = await db.execute(
            select(Plan).where(Plan.price_paise == 0, Plan.is_active == True).limit(1)
        )
        plan = result.scalars().first()

    if plan and plan.max_profile_photos is not None:
        return plan.max_profile_photos

    return settings.MAX_PHOTOS_PER_USER
