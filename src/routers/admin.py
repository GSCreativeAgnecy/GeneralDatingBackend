import csv
import io
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, case, String
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.auth_deps import get_current_admin
from core.exceptions import NotFoundException, ValidationException
from core.uploads import save_image_upload
from core.utils import get_max_photos_for_user
from models import (
    User, UserPhoto, UserLanguage, Match, Swipe, Message,
    BlockReport, Notification, Subscription, Plan, AppSetting, WaitlistSubscriber,
)
from schemas import (
    AdminDashboardOut, AdminReportOut, AdminHandleReportRequest,
    AdminUserOut, AdminUserDetailOut, AdminPhotoOut,
    AdminSubscriptionOut, AdminChatOut, AdminMessageOut,
    AdminUserUpdateRequest, AdminPlanOut, AdminPlanSaveRequest,
    AdminLimitsOut, AdminLimitsUpdateRequest, AdminWaitlistOut,
    AdminMatchUpdateRequest, SuccessResponse, AdminCreateUserRequest,
    AdminEditUserRequest, AdminResetPasswordRequest, AdminUserStatsOut,
    AdminSwipeItem, AdminMatchItem, AdminMessageItem,
    AdminPaginatedSwipes, AdminPaginatedMatches, AdminPaginatedMessages,
    AdminCreateMatchRequest, AdminAssignPlanRequest,
    BrandingSettingsUpdate, CurrencySettingUpdate,
    TwilioSettingsUpdate, AndroidSmsSettingsUpdate, OtpProviderUpdate,
    SmtpSettingsUpdate,
    StripeSettingsUpdate, RazorpaySettingsUpdate,
    PaypalSettingsUpdate, HelcimSettingsUpdate,
    ActivePaymentProcessorsUpdate,
    SettingsDashboardResponse,
)
from generate_dummy_data import generate as generate_dummy, reset_dummy_data

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardOut)
async def get_dashboard(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    active_today = (await db.execute(
        select(func.count()).select_from(User).where(User.last_active >= today_start)
    )).scalar()
    matches_today = (await db.execute(
        select(func.count()).select_from(Match).where(Match.matched_at >= today_start)
    )).scalar()
    reports_pending = (await db.execute(
        select(func.count()).select_from(BlockReport).where(BlockReport.type == "report")
    )).scalar()
    premium_users = (await db.execute(
        select(func.count()).select_from(User).where(User.is_premium == True)
    )).scalar()
    total_photos = (await db.execute(select(func.count()).select_from(UserPhoto))).scalar()
    total_swipes = (await db.execute(select(func.count()).select_from(Swipe))).scalar()
    total_messages = (await db.execute(select(func.count()).select_from(Message))).scalar()
    total_waitlist = (await db.execute(select(func.count()).select_from(WaitlistSubscriber))).scalar()
    total_matches = (await db.execute(select(func.count()).select_from(Match))).scalar()

    return AdminDashboardOut(
        total_users=total_users,
        active_users_today=active_today,
        matches_today=matches_today,
        reports_pending=reports_pending,
        premium_users=premium_users,
        total_photos=total_photos,
        total_swipes=total_swipes,
        total_messages=total_messages,
        total_waitlist=total_waitlist,
        total_matches=total_matches,
    )


@router.get("/users", response_model=list[AdminUserOut])
async def get_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200),
    search: str = Query(default=""),
    sort_by: str = Query(default="id"),
    sort_dir: str = Query(default="asc"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    sort_map = {
        "id": User.id,
        "first_name": User.first_name,
        "phone": User.phone_number,
        "city": User.city,
        "gender": User.gender,
        "status": User.is_active,
        "premium": User.is_premium,
        "created": User.created_at,
    }
    sort_col = sort_map.get(sort_by, User.id)
    if sort_dir not in ("asc", "desc"):
        sort_dir = "asc"

    stmt = select(User)
    if search:
        stmt = stmt.where(
            (User.first_name.ilike(f"%{search}%"))
            | (User.phone_number.ilike(f"%{search}%"))
            | (User.city.ilike(f"%{search}%"))
        )
    stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    users = result.scalars().all()

    user_ids = [u.id for u in users]
    plan_map = {}
    if user_ids:
        sub_result = await db.execute(
            select(Subscription.user_id, Plan.name).join(Plan, Plan.id == Subscription.plan_id).where(
                Subscription.user_id.in_(user_ids), Subscription.is_active == True
            )
        )
        plan_map = {row[0]: row[1] for row in sub_result.all()}

    count_stmt = select(func.count()).select_from(User)
    if search:
        count_stmt = count_stmt.where(
            (User.first_name.ilike(f"%{search}%"))
            | (User.phone_number.ilike(f"%{search}%"))
            | (User.city.ilike(f"%{search}%"))
        )
    total = (await db.execute(count_stmt)).scalar()

    return [
        AdminUserOut(
            id=u.id, first_name=u.first_name, last_name=u.last_name or "", phone_number=u.phone_number, city=u.city,
            gender=u.gender, plan_name=plan_map.get(u.id, "free"),
            is_active=u.is_active, is_premium=u.is_premium,
            phone_verified=u.phone_verified, photo_verified=u.photo_verified,
            profile_complete=u.profile_complete, created_at=u.created_at,
        )
        for u in users
    ]


# ── Import / Export (must be before /{user_id} routes) ──

@router.get("/users/export")
async def export_users(
    fmt: str = Query(default="json"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()

    rows = []
    for u in users:
        rows.append({
            "phone_number": u.phone_number, "first_name": u.first_name,
            "date_of_birth": u.date_of_birth, "gender": u.gender,
            "bio": u.bio or "", "intent": u.intent, "city": u.city,
            "college": u.college or "", "workplace": u.workplace or "",
            "height_cm": u.height_cm or "", "religion": u.religion or "",
            "education": u.education or "", "occupation": u.occupation or "",
            "is_premium": u.is_premium, "is_active": u.is_active,
            "phone_verified": u.phone_verified, "photo_verified": u.photo_verified,
            "created_at": u.created_at.isoformat() if u.created_at else "",
        })

    if fmt == "csv":
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users_export.csv"},
        )

    return rows


@router.post("/users/import")
async def import_users(
    file: UploadFile = File(...),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.endswith(".json"):
        raise ValidationException("Please upload a .json file")

    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise ValidationException("Invalid JSON file")

    if not isinstance(data, list):
        raise ValidationException("JSON must be an array of users")

    from core.security import hash_password

    created = 0
    skipped = 0
    for item in data:
        phone = str(item.get("phone_number", "")).strip()
        if not phone:
            skipped += 1
            continue
        existing = await db.execute(select(User).where(User.phone_number == phone))
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        db.add(User(
            phone_number=phone,
            phone_verified=bool(item.get("phone_verified", True)),
            password_hash=hash_password(phone),
            first_name=str(item.get("first_name", item.get("name", "User"))),
            date_of_birth=str(item.get("date_of_birth", "2000-01-01")),
            gender=str(item.get("gender", "")),
            bio=str(item.get("bio", "") or ""),
            intent=str(item.get("intent", "lets_see")),
            city=str(item.get("city", "")),
            college=str(item.get("college", "") or ""),
            workplace=str(item.get("workplace", "") or ""),
            height_cm=int(item.get("height_cm")) if item.get("height_cm") else None,
            religion=str(item.get("religion", "") or ""),
            education=str(item.get("education", "") or ""),
            occupation=str(item.get("occupation", "") or ""),
            is_premium=bool(item.get("is_premium", False)),
            is_active=bool(item.get("is_active", True)),
            photo_verified=bool(item.get("photo_verified", False)),
            profile_complete=bool(item.get("first_name", item.get("name", ""))),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ))
        created += 1

    await db.flush()
    return {"created": created, "skipped": skipped, "message": f"Imported {created} users, skipped {skipped} duplicates"}


@router.get("/users/{user_id}", response_model=AdminUserDetailOut)
async def get_user_detail(
    user_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(
            joinedload(User.photos),
            joinedload(User.languages),
        ).where(User.id == user_id)
    )
    user = result.unique().scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    return AdminUserDetailOut.model_validate(user)


@router.get("/users/{user_id}/stats", response_model=AdminUserStatsOut)
async def get_user_stats(
    user_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    today = datetime.now(timezone.utc)

    total_swipes = (await db.execute(
        select(func.count()).select_from(Swipe).where(Swipe.swiper_id == user_id)
    )).scalar()

    total_likes = (await db.execute(
        select(func.count()).select_from(Swipe).where(
            Swipe.swiper_id == user_id, Swipe.direction.in_(("like", "super_like"))
        )
    )).scalar()

    total_passes = (await db.execute(
        select(func.count()).select_from(Swipe).where(
            Swipe.swiper_id == user_id, Swipe.direction == "pass"
        )
    )).scalar()

    total_matches = (await db.execute(
        select(func.count()).select_from(Match).where(
            ((Match.user1_id == user_id) | (Match.user2_id == user_id))
        )
    )).scalar()

    total_messages_sent = (await db.execute(
        select(func.count()).select_from(Message).where(Message.sender_id == user_id)
    )).scalar()

    total_messages_received = (await db.execute(
        select(func.count()).select_from(Message).join(Match).where(
            ((Match.user1_id == user_id) | (Match.user2_id == user_id)),
            Message.sender_id != user_id,
        )
    )).scalar()

    total_photos = (await db.execute(
        select(func.count()).select_from(UserPhoto).where(UserPhoto.user_id == user_id)
    )).scalar()

    total_reports_filed = (await db.execute(
        select(func.count()).select_from(BlockReport).where(
            BlockReport.reporter_id == user_id, BlockReport.type == "report"
        )
    )).scalar()

    total_reports_against = (await db.execute(
        select(func.count()).select_from(BlockReport).where(
            BlockReport.reported_id == user_id, BlockReport.type == "report"
        )
    )).scalar()

    total_blocks = (await db.execute(
        select(func.count()).select_from(BlockReport).where(
            BlockReport.reporter_id == user_id, BlockReport.type == "block"
        )
    )).scalar()

    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id, Subscription.is_active == True
        ).order_by(Subscription.ends_at.desc())
    )
    active_sub = sub_result.scalars().first()

    account_age = 0
    if user.created_at:
        account_age = (today - user.created_at).days

    return AdminUserStatsOut(
        total_swipes=total_swipes,
        total_likes=total_likes,
        total_passes=total_passes,
        total_matches=total_matches,
        total_messages_sent=total_messages_sent,
        total_messages_received=total_messages_received,
        total_photos=total_photos,
        total_reports_filed=total_reports_filed,
        total_reports_against=total_reports_against,
        total_blocks=total_blocks,
        account_age_days=account_age,
        subscription_active=active_sub is not None,
        subscription_plan=active_sub.plan_type if active_sub else "free",
        subscription_ends=active_sub.ends_at if active_sub else None,
        last_active=user.last_active,
    )


@router.get("/users/{user_id}/swipes", response_model=AdminPaginatedSwipes)
async def get_user_swipes(
    user_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise NotFoundException("User not found")

    total = (await db.execute(
        select(func.count()).select_from(Swipe).where(Swipe.swiper_id == user_id)
    )).scalar()

    U2 = aliased(User)
    sort_map = {
        "target_name": U2.first_name, "direction": Swipe.direction, "created_at": Swipe.created_at,
    }
    sort_col = sort_map.get(sort_by, Swipe.created_at)
    sort_order = sort_col.asc() if sort_dir == "asc" else sort_col.desc()

    stmt = (
        select(Swipe.id, Swipe.swiped_id.label("target_id"), U2.first_name.label("target_name"),
               Swipe.direction, Swipe.created_at)
        .join(U2, U2.id == Swipe.swiped_id)
        .where(Swipe.swiper_id == user_id)
        .order_by(sort_order)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = (await db.execute(stmt)).all()

    swiped_ids = [r.target_id for r in rows]
    matched_set = set()
    if swiped_ids:
        match_rows = await db.execute(
            select(Match.user1_id, Match.user2_id).where(
                ((Match.user1_id == user_id) & (Match.user2_id.in_(swiped_ids)))
                | ((Match.user2_id == user_id) & (Match.user1_id.in_(swiped_ids)))
            )
        )
        for m1, m2 in match_rows.all():
            other = m2 if m1 == user_id else m1
            matched_set.add(other)

    items = [
        AdminSwipeItem(
            id=r.id, target_id=r.target_id, target_name=r.target_name,
            direction=r.direction, matched=r.target_id in matched_set,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return AdminPaginatedSwipes(items=items, total=total)


@router.get("/users/{user_id}/matches", response_model=AdminPaginatedMatches)
async def get_user_matches(
    user_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="matched_at"),
    sort_dir: str = Query(default="desc"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise NotFoundException("User not found")

    total = (await db.execute(
        select(func.count()).select_from(Match).where(
            (Match.user1_id == user_id) | (Match.user2_id == user_id)
        )
    )).scalar()

    msg_count = (
        select(func.count(Message.id))
        .where(Message.match_id == Match.id)
        .correlate(Match)
        .scalar_subquery()
    )
    other_id_expr = case((Match.user1_id == user_id, Match.user2_id), else_=Match.user1_id)
    U = aliased(User)
    stmt = (
        select(Match, msg_count.label("msg_count"), other_id_expr.label("other_id"), U.first_name.label("other_name"),
               U.gender.label("other_gender"), U.city.label("other_city"))
        .join(U, U.id == other_id_expr)
        .where((Match.user1_id == user_id) | (Match.user2_id == user_id))
        .order_by(
            {"matched_at": Match.matched_at, "messages": msg_count,
             "active": Match.is_active, "name": U.first_name}.get(sort_by, Match.matched_at).desc()
            if sort_dir != "asc" else
            {"matched_at": Match.matched_at, "messages": msg_count,
             "active": Match.is_active, "name": U.first_name}.get(sort_by, Match.matched_at).asc()
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = (await db.execute(stmt)).all()

    items = []
    for m, msg_c, other_id, other_name, other_gender, other_city in rows:
        items.append(AdminMatchItem(
            id=m.id, other_id=other_id, other_name=other_name,
            other_gender=other_gender, other_city=other_city,
            is_active=m.is_active, message_count=msg_c,
            matched_at=m.matched_at,
        ))
    return AdminPaginatedMatches(items=items, total=total)


@router.get("/users/{user_id}/messages", response_model=AdminPaginatedMessages)
async def get_user_messages(
    user_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise NotFoundException("User not found")

    total = (await db.execute(
        select(func.count()).select_from(Message).where(Message.sender_id == user_id)
    )).scalar()

    receiver_expr = case((Match.user1_id == user_id, Match.user2_id), else_=Match.user1_id)
    R = aliased(User)
    stmt = (
        select(Message, receiver_expr.label("receiver_id"), R.first_name.label("receiver_name"))
        .join(Match, Match.id == Message.match_id)
        .join(R, R.id == receiver_expr)
        .where(Message.sender_id == user_id)
        .order_by(
            {"created_at": Message.created_at, "content": Message.content,
             "read": Message.is_read, "receiver_name": R.first_name}.get(sort_by, Message.created_at).asc()
            if sort_dir == "asc" else
            {"created_at": Message.created_at, "content": Message.content,
             "read": Message.is_read, "receiver_name": R.first_name}.get(sort_by, Message.created_at).desc()
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = (await db.execute(stmt)).all()

    items = []
    for m, rid, rname in rows:
        items.append(AdminMessageItem(
            id=m.id, match_id=m.match_id,
            receiver_id=rid, receiver_name=rname,
            content=m.content[:120] if m.content else "",
            is_read=m.is_read, created_at=m.created_at,
        ))
    return AdminPaginatedMessages(items=items, total=total)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    req: AdminUserUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    if req.is_active is not None:
        user.is_active = req.is_active
    if req.is_premium is not None:
        user.is_premium = req.is_premium
    if req.photo_verified is not None:
        user.photo_verified = req.photo_verified

    await db.flush()
    return SuccessResponse(message="User updated")


@router.put("/users/{user_id}", response_model=AdminUserDetailOut)
async def edit_user(
    user_id: int,
    req: AdminEditUserRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    for key, value in req.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    await db.flush()

    result = await db.execute(
        select(User).options(
            joinedload(User.photos),
            joinedload(User.languages),
        ).where(User.id == user_id)
    )
    return AdminUserDetailOut.model_validate(result.unique().scalar_one())


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    req: AdminResetPasswordRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    from core.security import hash_password
    user.password_hash = hash_password(req.password)
    await db.flush()
    return SuccessResponse(message="Password reset successfully")


@router.post("/users/{user_id}/assign-plan")
async def assign_user_plan(
    user_id: int,
    req: AdminAssignPlanRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    plan_result = await db.execute(select(Plan).where(Plan.id == req.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise NotFoundException("Plan not found")

    from datetime import timedelta
    now = datetime.now(timezone.utc)
    db.add(Subscription(
        user_id=user_id,
        plan_type=plan.name,
        plan_id=plan.id,
        starts_at=now,
        ends_at=now + timedelta(days=plan.duration_days or 30),
        is_active=True,
    ))
    user.is_premium = True

    old_subs = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
        )
    )
    for old in old_subs.scalars().all():
        if old.plan_id != req.plan_id:
            old.is_active = False

    await db.flush()
    return SuccessResponse(message=f"Plan '{plan.name}' assigned to {user.first_name}")


@router.post("/users/{user_id}/remove-plan")
async def remove_user_plan(
    user_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    subs = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id, Subscription.is_active == True)
    )
    for sub in subs.scalars().all():
        sub.is_active = False
    user.is_premium = False
    await db.flush()
    return SuccessResponse(message=f"Plan removed from {user.first_name}")


@router.post("/users", response_model=AdminUserOut)
async def create_user(
    req: AdminCreateUserRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(User).where(User.phone_number == req.phone_number.strip())
    )
    if existing.scalar_one_or_none():
        raise ValidationException("User with this phone number already exists")

    from core.security import hash_password

    user = User(
        phone_number=req.phone_number.strip(),
        phone_verified=True,
        password_hash=hash_password(req.phone_number.strip()),
        first_name=req.first_name,
        date_of_birth=req.date_of_birth or "2000-01-01",
        gender=req.gender or "male",
        city=req.city or "Mumbai",
        bio=req.bio,
        caste=req.caste,
        earnings=req.earnings,
        marital_status=req.marital_status,
        siblings=req.siblings,
        favorite_color=req.favorite_color,
        favorite_sports=req.favorite_sports,
        is_premium=req.is_premium,
        profile_complete=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    return AdminUserOut(
        id=user.id, first_name=user.first_name, last_name=user.last_name or "",
        phone_number=user.phone_number, city=user.city, gender=user.gender,
        is_active=user.is_active, is_premium=user.is_premium,
        phone_verified=user.phone_verified, photo_verified=user.photo_verified,
        profile_complete=user.profile_complete, created_at=user.created_at,
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    await db.delete(user)
    await db.flush()
    return SuccessResponse(message="User deleted")


@router.get("/photos", response_model=list[AdminPhotoOut])
async def get_photos(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    search: str = Query(default=""),
    sort_by: str = Query(default="id"),
    sort_dir: str = Query(default="asc"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserPhoto, User.first_name)
        .join(User, User.id == UserPhoto.user_id)
    )
    if search:
        stmt = stmt.where(
            User.first_name.ilike(f"%{search}%") | UserPhoto.id.cast(String).ilike(f"%{search}%")
        )

    sort_map = {
        "id": UserPhoto.id, "user_name": User.first_name,
        "is_primary": UserPhoto.is_primary, "created_at": UserPhoto.created_at,
    }
    sort_col = sort_map.get(sort_by, UserPhoto.id)
    stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    rows = result.all()
    return [
        AdminPhotoOut(
            id=p.id, user_id=p.user_id, user_name=name,
            photo_url=p.photo_url, is_primary=p.is_primary,
            created_at=p.created_at,
        )
        for p, name in rows
    ]


@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserPhoto).where(UserPhoto.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise NotFoundException("Photo not found")
    await db.delete(photo)
    await db.flush()
    return SuccessResponse(message="Photo deleted")


@router.post("/photos", response_model=AdminPhotoOut)
async def upload_photo(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    existing = (await db.execute(
        select(UserPhoto).where(UserPhoto.user_id == user_id)
    )).scalars().all()
    max_photos = await get_max_photos_for_user(user_id, db)
    if len(existing) >= max_photos:
        raise ValidationException(f"Maximum {max_photos} photos allowed for this user")

    photo_url = await save_image_upload(file, user.id)

    is_primary = len(existing) == 0
    photo = UserPhoto(
        user_id=user.id,
        photo_url=photo_url,
        is_primary=is_primary,
        sort_order=len(existing),
    )
    db.add(photo)
    await db.flush()

    return AdminPhotoOut(
        id=photo.id,
        user_id=photo.user_id,
        user_name=user.first_name,
        photo_url=photo.photo_url,
        is_primary=photo.is_primary,
        created_at=photo.created_at,
    )


@router.get("/subscriptions", response_model=list[AdminSubscriptionOut])
async def get_subscriptions(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    search: str = Query(default=""),
    sort_by: str = Query(default="id"),
    sort_dir: str = Query(default="asc"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Subscription, User.first_name)
        .join(User, User.id == Subscription.user_id)
    )
    if search:
        stmt = stmt.where(
            User.first_name.ilike(f"%{search}%") | Subscription.plan_type.ilike(f"%{search}%")
        )
    sort_map = {
        "id": Subscription.id, "user_name": User.first_name,
        "plan_type": Subscription.plan_type, "starts_at": Subscription.starts_at,
        "ends_at": Subscription.ends_at, "is_active": Subscription.is_active,
    }
    sort_col = sort_map.get(sort_by, Subscription.id)
    stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    rows = result.all()
    return [
        AdminSubscriptionOut(
            id=s.id, user_id=s.user_id, user_name=name,
            plan_type=s.plan_type, starts_at=s.starts_at,
            ends_at=s.ends_at, is_active=s.is_active,
        )
        for s, name in rows
    ]


@router.get("/chats", response_model=list[AdminChatOut])
async def get_chats(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    U1 = aliased(User)
    U2 = aliased(User)
    last_content = (
        select(Message.content)
        .where(Message.match_id == Match.id)
        .order_by(Message.created_at.desc())
        .limit(1)
        .correlate(Match)
        .scalar_subquery()
    )
    last_time = (
        select(Message.created_at)
        .where(Message.match_id == Match.id)
        .order_by(Message.created_at.desc())
        .limit(1)
        .correlate(Match)
        .scalar_subquery()
    )
    stmt = (
        select(
            Match.id,
            Match.user1_id,
            Match.user2_id,
            U1.first_name.label("user1_name"),
            U2.first_name.label("user2_name"),
            Match.matched_at,
            Match.is_active,
            func.count(Message.id).label("message_count"),
            last_content.label("last_message"),
            last_time.label("last_message_at"),
        )
        .join(U1, U1.id == Match.user1_id)
        .join(U2, U2.id == Match.user2_id)
        .outerjoin(Message, Message.match_id == Match.id)
        .group_by(Match.id, U1.first_name, U2.first_name)
        .order_by(Match.matched_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        AdminChatOut(
            id=row.id,
            user1_id=row.user1_id,
            user2_id=row.user2_id,
            user1_name=row.user1_name,
            user2_name=row.user2_name,
            matched_at=row.matched_at,
            is_active=row.is_active,
            message_count=row.message_count,
            last_message=row.last_message,
            last_message_at=row.last_message_at,
        )
        for row in rows
    ]


@router.get("/chats/{match_id}/messages", response_model=list[AdminMessageOut])
async def get_chat_messages(
    match_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    if not result.scalar_one_or_none():
        raise NotFoundException("Match not found")

    stmt = (
        select(Message.id, Message.sender_id, User.first_name.label("sender_name"),
               Message.message_type, Message.content, Message.is_read, Message.created_at)
        .join(User, User.id == Message.sender_id)
        .where(Message.match_id == match_id)
        .order_by(Message.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        AdminMessageOut(
            id=row.id,
            sender_id=row.sender_id,
            sender_name=row.sender_name,
            message_type=row.message_type,
            content=row.content,
            is_read=row.is_read,
            created_at=row.created_at,
        )
        for row in rows
    ]


# ── Matches ──

@router.get("/matches", response_model=list[AdminChatOut])
async def get_matches(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200),
    status: str = Query(default="all"),
    search: str = Query(default=""),
    sort_by: str = Query(default="id"),
    sort_dir: str = Query(default="asc"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    U1 = aliased(User)
    U2 = aliased(User)
    last_content = (
        select(Message.content)
        .where(Message.match_id == Match.id)
        .order_by(Message.created_at.desc())
        .limit(1)
        .correlate(Match)
        .scalar_subquery()
    )
    last_time = (
        select(Message.created_at)
        .where(Message.match_id == Match.id)
        .order_by(Message.created_at.desc())
        .limit(1)
        .correlate(Match)
        .scalar_subquery()
    )
    msg_count_sub = (
        select(func.count(Message.id))
        .where(Message.match_id == Match.id)
        .correlate(Match)
        .scalar_subquery()
    )
    stmt = (
        select(
            Match.id,
            Match.user1_id,
            Match.user2_id,
            U1.first_name.label("user1_name"),
            U2.first_name.label("user2_name"),
            Match.matched_at,
            Match.is_active,
            msg_count_sub.label("message_count"),
            last_content.label("last_message"),
            last_time.label("last_message_at"),
        )
        .join(U1, U1.id == Match.user1_id)
        .join(U2, U2.id == Match.user2_id)
    )
    if search:
        stmt = stmt.where(
            U1.first_name.ilike(f"%{search}%") | U2.first_name.ilike(f"%{search}%")
        )
    if status == "active":
        stmt = stmt.where(Match.is_active == True)
    elif status == "inactive":
        stmt = stmt.where(Match.is_active == False)

    sort_map = {
        "id": Match.id, "user1_name": U1.first_name, "user2_name": U2.first_name,
        "messages": msg_count_sub, "matched_at": Match.matched_at,
        "status": Match.is_active,
    }
    sort_col = sort_map.get(sort_by, Match.id)
    order_fn = lambda c: c.asc() if sort_dir == "asc" else c.desc()
    stmt = stmt.order_by(order_fn(sort_col)).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    rows = result.all()
    return [
        AdminChatOut(
            id=row.id,
            user1_id=row.user1_id,
            user2_id=row.user2_id,
            user1_name=row.user1_name,
            user2_name=row.user2_name,
            matched_at=row.matched_at,
            is_active=row.is_active,
            message_count=row.message_count,
            last_message=row.last_message,
            last_message_at=row.last_message_at,
        )
        for row in rows
    ]


@router.post("/matches")
async def create_match(
    req: AdminCreateMatchRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if req.user1_id == req.user2_id:
        raise ValidationException("Cannot match a user with themselves")

    user1 = await db.execute(select(User).where(User.id == req.user1_id))
    user2 = await db.execute(select(User).where(User.id == req.user2_id))
    if not user1.scalar_one_or_none() or not user2.scalar_one_or_none():
        raise NotFoundException("One or both users not found")

    u1, u2 = (req.user1_id, req.user2_id) if req.user1_id < req.user2_id else (req.user2_id, req.user1_id)

    existing = await db.execute(
        select(Match).where(Match.user1_id == u1, Match.user2_id == u2)
    )
    if existing.scalar_one_or_none():
        raise ValidationException("Match already exists between these users")

    match = Match(user1_id=u1, user2_id=u2)
    db.add(match)
    await db.flush()

    u1name = (await db.execute(select(User.first_name).where(User.id == req.user1_id))).scalar()
    u2name = (await db.execute(select(User.first_name).where(User.id == req.user2_id))).scalar()

    return {
        "success": True,
        "match_id": match.id,
        "message": f"Match created between {u1name} and {u2name}",
    }


@router.patch("/matches/{match_id}")
async def update_match(
    match_id: int,
    req: AdminMatchUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise NotFoundException("Match not found")
    if req.is_active is not None:
        match.is_active = req.is_active
    await db.flush()
    return SuccessResponse(message="Match updated")


@router.delete("/matches/{match_id}")
async def delete_match(
    match_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise NotFoundException("Match not found")
    await db.delete(match)
    await db.flush()
    return SuccessResponse(message="Match deleted")


# ── Plans ──

@router.get("/plans", response_model=list[AdminPlanOut])
async def get_plans(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).order_by(Plan.sort_order))
    return [AdminPlanOut.model_validate(p) for p in result.scalars().all()]


@router.post("/plans", response_model=AdminPlanOut)
async def create_plan(
    req: AdminPlanSaveRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    plan = Plan(
        name=req.name,
        price_paise=req.price_paise,
        duration_days=req.duration_days,
        swipes_per_day=req.swipes_per_day,
        super_likes_per_day=req.super_likes_per_day,
        messages=req.messages,
        photos_in_inbox_per_day=req.photos_in_inbox_per_day,
        max_profile_photos=req.max_profile_photos,
        boosts_per_month=req.boosts_per_month,
        see_who_liked_you=req.see_who_liked_you,
        no_ads=req.no_ads,
        read_receipts=req.read_receipts,
        incognito_mode=req.incognito_mode,
        verified_badge=req.verified_badge,
        is_active=req.is_active,
        sort_order=req.sort_order,
    )
    db.add(plan)
    await db.flush()
    return AdminPlanOut.model_validate(plan)


@router.put("/plans/{plan_id}", response_model=AdminPlanOut)
async def update_plan(
    plan_id: int,
    req: AdminPlanSaveRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise NotFoundException("Plan not found")
    plan.name = req.name
    plan.price_paise = req.price_paise
    plan.duration_days = req.duration_days
    plan.swipes_per_day = req.swipes_per_day
    plan.super_likes_per_day = req.super_likes_per_day
    plan.messages = req.messages
    plan.photos_in_inbox_per_day = req.photos_in_inbox_per_day
    plan.max_profile_photos = req.max_profile_photos
    plan.boosts_per_month = req.boosts_per_month
    plan.see_who_liked_you = req.see_who_liked_you
    plan.no_ads = req.no_ads
    plan.read_receipts = req.read_receipts
    plan.incognito_mode = req.incognito_mode
    plan.verified_badge = req.verified_badge
    plan.is_active = req.is_active
    plan.sort_order = req.sort_order
    await db.flush()
    return AdminPlanOut.model_validate(plan)


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise NotFoundException("Plan not found")
    if plan.price_paise == 0 and plan.duration_days == 0:
        raise ValidationException("Cannot delete the Free plan")
    await db.delete(plan)
    await db.flush()
    return SuccessResponse(message="Plan deleted")


# ── Limits ──

@router.get("/limits", response_model=AdminLimitsOut)
async def get_limits(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AppSetting))
    stored = {s.key: s.value for s in result.scalars().all()}
    return AdminLimitsOut(
        max_photos_per_user=int(stored.get("max_photos_per_user", settings.MAX_PHOTOS_PER_USER)),
        max_photo_size_mb=int(stored.get("max_photo_size_mb", settings.MAX_PHOTO_SIZE_MB)),
        family_share_expire_days=int(stored.get("family_share_expire_days", settings.FAMILY_SHARE_EXPIRE_DAYS)),
    )


@router.put("/limits", response_model=AdminLimitsOut)
async def update_limits(
    req: AdminLimitsUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updates = {
        "max_photos_per_user": req.max_photos_per_user,
        "max_photo_size_mb": req.max_photo_size_mb,
        "family_share_expire_days": req.family_share_expire_days,
    }
    for key, val in updates.items():
        if val is not None:
            result = await db.execute(select(AppSetting).where(AppSetting.key == key))
            existing = result.scalar_one_or_none()
            if existing:
                existing.value = str(val)
            else:
                db.add(AppSetting(key=key, value=str(val)))

    await db.flush()

    result = await db.execute(select(AppSetting))
    raw = {s.key: s.value for s in result.scalars().all()}
    if "max_photos_per_user" in raw:
        settings.MAX_PHOTOS_PER_USER = int(raw["max_photos_per_user"])
    if "max_photo_size_mb" in raw:
        settings.MAX_PHOTO_SIZE_MB = int(raw["max_photo_size_mb"])
    if "family_share_expire_days" in raw:
        settings.FAMILY_SHARE_EXPIRE_DAYS = int(raw["family_share_expire_days"])

    return AdminLimitsOut(
        max_photos_per_user=settings.MAX_PHOTOS_PER_USER,
        max_photo_size_mb=settings.MAX_PHOTO_SIZE_MB,
        family_share_expire_days=settings.FAMILY_SHARE_EXPIRE_DAYS,
    )


@router.get("/reports", response_model=list[AdminReportOut])
async def get_reports(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=""),
    sort_by: str = Query(default="id"),
    sort_dir: str = Query(default="asc"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    R1 = aliased(User)
    R2 = aliased(User)
    stmt = (
        select(BlockReport.id, BlockReport.reporter_id, BlockReport.reported_id,
               R1.first_name.label("reporter_name"), R2.first_name.label("reported_name"),
               BlockReport.reason, BlockReport.created_at)
        .join(R1, R1.id == BlockReport.reporter_id)
        .join(R2, R2.id == BlockReport.reported_id)
        .where(BlockReport.type == "report")
    )
    if search:
        stmt = stmt.where(
            R1.first_name.ilike(f"%{search}%") | R2.first_name.ilike(f"%{search}%")
            | BlockReport.reason.ilike(f"%{search}%")
        )

    sort_map = {
        "id": BlockReport.id, "reporter_name": R1.first_name,
        "reported_name": R2.first_name, "reason": BlockReport.reason,
        "created_at": BlockReport.created_at,
    }
    sort_col = sort_map.get(sort_by, BlockReport.id)
    stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    rows = result.all()

    return [
        AdminReportOut(
            id=r.id, reporter_id=r.reporter_id, reported_id=r.reported_id,
            reporter_name=r.reporter_name, reported_name=r.reported_name,
            reason=r.reason, created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/reports/{report_id}/action")
async def handle_report(
    report_id: int,
    req: AdminHandleReportRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BlockReport).where(BlockReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundException("Report not found")

    if req.action == "ban":
        user_result = await db.execute(select(User).where(User.id == report.reported_id))
        target = user_result.scalar_one_or_none()
        if target:
            target.is_active = False
    elif req.action == "dismiss":
        pass

    await db.delete(report)
    await db.flush()
    return SuccessResponse(message=f"Report handled: {req.action}")


@router.get("/waitlist", response_model=list[AdminWaitlistOut])
async def get_waitlist(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    search: str = Query(default=""),
    sort_by: str = Query(default="id"),
    sort_dir: str = Query(default="asc"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(WaitlistSubscriber)
    if search:
        stmt = stmt.where(
            WaitlistSubscriber.name.ilike(f"%{search}%")
            | WaitlistSubscriber.email.ilike(f"%{search}%")
        )
    sort_map = {
        "id": WaitlistSubscriber.id, "name": WaitlistSubscriber.name,
        "email": WaitlistSubscriber.email, "created_at": WaitlistSubscriber.created_at,
    }
    sort_col = sort_map.get(sort_by, WaitlistSubscriber.id)
    stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    return [AdminWaitlistOut.model_validate(s) for s in result.scalars().all()]


@router.get("/waitlist/export")
async def export_waitlist(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WaitlistSubscriber.name, WaitlistSubscriber.email, WaitlistSubscriber.created_at)
        .order_by(WaitlistSubscriber.id.asc())
    )
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Joined"])
    for name, email, created_at in rows:
        writer.writerow([name, email, created_at.strftime("%Y-%m-%d %H:%M") if created_at else ""])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=waitlist_subscribers.csv"},
    )


@router.get("/stats/gender")
async def get_gender_stats(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User.gender, func.count()).group_by(User.gender)
    )
    return {g: c for g, c in result.all()}


@router.get("/stats/cities")
async def get_city_stats(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User.city, func.count()).group_by(User.city).order_by(func.count().desc()).limit(20)
    )
    return [{"city": c, "count": cnt} for c, cnt in result.all() if c]


# ── Dummy Data ──

@router.post("/dummy-data/generate")
async def create_dummy_data(
    male_count: int = Query(default=10, ge=0, le=500),
    female_count: int = Query(default=10, ge=0, le=1500),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    async def event_stream():
        async for event in generate_dummy(db, male_count=male_count, female_count=female_count):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/dummy-data/reset")
async def clear_dummy_data(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await reset_dummy_data(db)
    return result


# ── White-Label Settings ──

async def _save_settings(db: AsyncSession, updates: dict):
    for key, val in updates.items():
        existing = (await db.execute(select(AppSetting).where(AppSetting.key == key))).scalar_one_or_none()
        if existing:
            existing.value = str(val)
        else:
            db.add(AppSetting(key=key, value=str(val)))


async def _get_all_stored(db: AsyncSession) -> dict:
    result = await db.execute(select(AppSetting))
    return {s.key: s.value for s in result.scalars().all()}


def _get_stored(stored: dict, key: str, default: str = "") -> str:
    return str(stored.get(key, default))


def _get_stored_int(stored: dict, key: str, default: int = 0) -> int:
    try:
        return int(stored.get(key, default))
    except (ValueError, TypeError):
        return default


def _build_settings_response(stored: dict) -> SettingsDashboardResponse:
    from core.stripe import mask_key

    stripe_secret = _get_stored(stored, "stripe_secret_key", settings.STRIPE_SECRET_KEY)
    stripe_webhook = _get_stored(stored, "stripe_webhook_secret", settings.STRIPE_WEBHOOK_SECRET)
    razorpay_secret = _get_stored(stored, "razorpay_key_secret", settings.RAZORPAY_KEY_SECRET)
    razorpay_webhook = _get_stored(stored, "razorpay_webhook_secret", settings.RAZORPAY_WEBHOOK_SECRET)
    paypal_secret = _get_stored(stored, "paypal_client_secret", settings.PAYPAL_CLIENT_SECRET)
    twilio_token = _get_stored(stored, "twilio_auth_token", settings.TWILIO_AUTH_TOKEN)
    smtp_password = _get_stored(stored, "smtp_password", settings.SMTP_PASSWORD)
    helcim_token = _get_stored(stored, "helcim_api_token", settings.HELCIM_API_TOKEN)
    android_key = _get_stored(stored, "android_sms_gateway_api_key", settings.ANDROID_SMS_GATEWAY_API_KEY)

    active_processors_raw = _get_stored(stored, "active_payment_processors", settings.ACTIVE_PAYMENT_PROCESSORS)
    active_processors = [p.strip() for p in active_processors_raw.split(",") if p.strip()] if active_processors_raw else []

    return SettingsDashboardResponse(
        app_name=_get_stored(stored, "app_name", settings.APP_NAME),
        primary_color=_get_stored(stored, "primary_color", settings.PRIMARY_COLOR),
        secondary_color=_get_stored(stored, "secondary_color", settings.SECONDARY_COLOR),
        accent_color=_get_stored(stored, "accent_color", settings.ACCENT_COLOR),
        logo_url=_get_stored(stored, "logo_url", settings.LOGO_URL),
        default_currency=_get_stored(stored, "default_currency", settings.DEFAULT_CURRENCY),
        active_payment_processors=active_processors,
        stripe_public_key=_get_stored(stored, "stripe_public_key", settings.STRIPE_PUBLIC_KEY),
        stripe_secret_key=mask_key(stripe_secret),
        stripe_webhook_secret=mask_key(stripe_webhook),
        razorpay_key_id=mask_key(_get_stored(stored, "razorpay_key_id", settings.RAZORPAY_KEY_ID)),
        razorpay_key_secret=mask_key(razorpay_secret),
        razorpay_webhook_secret=mask_key(razorpay_webhook),
        paypal_client_id=mask_key(_get_stored(stored, "paypal_client_id", settings.PAYPAL_CLIENT_ID)),
        paypal_client_secret=mask_key(paypal_secret),
        paypal_webhook_id=_get_stored(stored, "paypal_webhook_id", settings.PAYPAL_WEBHOOK_ID),
        paypal_mode=_get_stored(stored, "paypal_mode", settings.PAYPAL_MODE),
        helcim_api_token=mask_key(helcim_token),
        helcim_account_id=_get_stored(stored, "helcim_account_id", settings.HELCIM_ACCOUNT_ID),
        helcim_webhook_secret=mask_key(_get_stored(stored, "helcim_webhook_secret", settings.HELCIM_WEBHOOK_SECRET)),
        helcim_mode=_get_stored(stored, "helcim_mode", settings.HELCIM_MODE),
        preferred_otp_provider=_get_stored(stored, "preferred_otp_provider", settings.PREFERRED_OTP_PROVIDER),
        twilio_account_sid=_get_stored(stored, "twilio_account_sid", settings.TWILIO_ACCOUNT_SID),
        twilio_auth_token=mask_key(twilio_token),
        twilio_phone=_get_stored(stored, "twilio_phone", settings.TWILIO_PHONE),
        android_sms_gateway_url=_get_stored(stored, "android_sms_gateway_url", settings.ANDROID_SMS_GATEWAY_URL),
        android_sms_gateway_api_key=mask_key(android_key),
        smtp_host=_get_stored(stored, "smtp_host", settings.SMTP_HOST),
        smtp_port=_get_stored_int(stored, "smtp_port", settings.SMTP_PORT),
        smtp_user=_get_stored(stored, "smtp_user", settings.SMTP_USER),
        smtp_password=mask_key(smtp_password),
        smtp_from_name=_get_stored(stored, "smtp_from_name", settings.SMTP_FROM_NAME),
        notify_email=_get_stored(stored, "notify_email", settings.NOTIFY_EMAIL),
    )


@router.get("/settings", response_model=SettingsDashboardResponse)
async def get_settings(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


@router.put("/settings/branding", response_model=SettingsDashboardResponse)
async def update_branding(
    req: BrandingSettingsUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    import re
    hex_pattern = re.compile(r"^#([A-Fa-f0-9]{6})$")

    updates = {}
    if req.app_name is not None:
        updates["app_name"] = req.app_name.strip()
    if req.primary_color is not None:
        if not hex_pattern.match(req.primary_color.strip()):
            raise ValidationException("primary_color must be a valid hex color (e.g. #3B82F6)")
        updates["primary_color"] = req.primary_color.strip()
    if req.secondary_color is not None:
        if not hex_pattern.match(req.secondary_color.strip()):
            raise ValidationException("secondary_color must be a valid hex color (e.g. #1E3A8A)")
        updates["secondary_color"] = req.secondary_color.strip()
    if req.accent_color is not None:
        if not hex_pattern.match(req.accent_color.strip()):
            raise ValidationException("accent_color must be a valid hex color (e.g. #10B981)")
        updates["accent_color"] = req.accent_color.strip()
    if req.logo_url is not None:
        updates["logo_url"] = req.logo_url.strip()

    await _save_settings(db, updates)

    if "app_name" in updates:
        settings.APP_NAME = updates["app_name"]
    if "primary_color" in updates:
        settings.PRIMARY_COLOR = updates["primary_color"]
    if "secondary_color" in updates:
        settings.SECONDARY_COLOR = updates["secondary_color"]
    if "accent_color" in updates:
        settings.ACCENT_COLOR = updates["accent_color"]
    if "logo_url" in updates:
        settings.LOGO_URL = updates["logo_url"]

    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


@router.post("/settings/branding/logo", response_model=SettingsDashboardResponse)
async def upload_logo(
    file: UploadFile = File(...),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    allowed_ext = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
    allowed_mimes = {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}

    ext = ""
    if file.filename and "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower()

    if ext not in allowed_ext:
        raise ValidationException(f"Logo must be a PNG, JPG, WEBP, or SVG file. Got: {ext}")

    if file.content_type and file.content_type not in allowed_mimes:
        raise ValidationException(f"Unsupported image type: {file.content_type}")

    contents = await file.read()
    max_size = 2 * 1024 * 1024  # 2 MB
    if len(contents) > max_size:
        raise ValidationException("Logo file must be under 2 MB")

    import secrets
    logo_dir = settings.UPLOAD_DIR / "logos"
    logo_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"logo_{secrets.token_hex(8)}{ext}"
    logo_path = logo_dir / safe_name
    logo_path.write_bytes(contents)

    logo_url = f"/api/v1/uploads/logos/{safe_name}"
    updates = {"logo_url": logo_url}
    await _save_settings(db, updates)
    settings.LOGO_URL = logo_url

    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


# ── Currency ──

@router.put("/settings/currency", response_model=SettingsDashboardResponse)
async def update_currency(
    req: CurrencySettingUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from schemas import ALLOWED_CURRENCIES
    cur = req.currency.strip().upper()
    if cur not in ALLOWED_CURRENCIES:
        raise ValidationException(f"Invalid currency '{cur}'. Allowed: {', '.join(ALLOWED_CURRENCIES)}")

    await _save_settings(db, {"default_currency": cur})
    settings.DEFAULT_CURRENCY = cur
    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


# ── OTP Provider ──

@router.put("/settings/otp-provider", response_model=SettingsDashboardResponse)
async def update_otp_provider(
    req: OtpProviderUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from schemas import ALLOWED_OTP_PROVIDERS
    provider = req.preferred_otp_provider.strip().lower()
    if provider not in ALLOWED_OTP_PROVIDERS:
        raise ValidationException(f"Invalid OTP provider '{provider}'. Allowed: {', '.join(ALLOWED_OTP_PROVIDERS)}")

    await _save_settings(db, {"preferred_otp_provider": provider})
    settings.PREFERRED_OTP_PROVIDER = provider
    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


# ── Twilio Settings ──

@router.put("/settings/twilio", response_model=SettingsDashboardResponse)
async def update_twilio(
    req: TwilioSettingsUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updates = {}
    if req.twilio_account_sid is not None:
        updates["twilio_account_sid"] = req.twilio_account_sid.strip()
    if req.twilio_auth_token is not None:
        updates["twilio_auth_token"] = req.twilio_auth_token.strip()
    if req.twilio_phone is not None:
        updates["twilio_phone"] = req.twilio_phone.strip()

    await _save_settings(db, updates)
    for key, val in updates.items():
        setattr(settings, key.upper(), val)
    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


# ── Android SMS Gateway Settings ──

@router.put("/settings/android-sms", response_model=SettingsDashboardResponse)
async def update_android_sms(
    req: AndroidSmsSettingsUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updates = {}
    if req.android_sms_gateway_url is not None:
        updates["android_sms_gateway_url"] = req.android_sms_gateway_url.strip()
        if updates["android_sms_gateway_url"] and not updates["android_sms_gateway_url"].startswith("http"):
            raise ValidationException("Gateway URL must start with http:// or https://")
    if req.android_sms_gateway_api_key is not None:
        updates["android_sms_gateway_api_key"] = req.android_sms_gateway_api_key.strip()

    await _save_settings(db, updates)
    for key, val in updates.items():
        setattr(settings, key.upper(), val)
    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


# ── SMTP Settings ──

@router.put("/settings/smtp", response_model=SettingsDashboardResponse)
async def update_smtp(
    req: SmtpSettingsUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updates = {}
    if req.smtp_host is not None:
        updates["smtp_host"] = req.smtp_host.strip()
    if req.smtp_port is not None:
        if req.smtp_port < 1 or req.smtp_port > 65535:
            raise ValidationException("smtp_port must be between 1 and 65535")
        updates["smtp_port"] = str(req.smtp_port)
    if req.smtp_user is not None:
        updates["smtp_user"] = req.smtp_user.strip()
    if req.smtp_password is not None:
        updates["smtp_password"] = req.smtp_password.strip()
    if req.smtp_from_name is not None:
        updates["smtp_from_name"] = req.smtp_from_name.strip()
    if req.notify_email is not None:
        updates["notify_email"] = req.notify_email.strip()

    await _save_settings(db, updates)
    if "smtp_host" in updates:
        settings.SMTP_HOST = updates["smtp_host"]
    if "smtp_port" in updates:
        settings.SMTP_PORT = int(updates["smtp_port"])
    if "smtp_user" in updates:
        settings.SMTP_USER = updates["smtp_user"]
    if "smtp_password" in updates:
        settings.SMTP_PASSWORD = updates["smtp_password"]
    if "smtp_from_name" in updates:
        settings.SMTP_FROM_NAME = updates["smtp_from_name"]
    if "notify_email" in updates:
        settings.NOTIFY_EMAIL = updates["notify_email"]
    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


# ── Stripe Settings ──

@router.put("/settings/stripe", response_model=SettingsDashboardResponse)
async def update_stripe(
    req: StripeSettingsUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    import re
    secret_pattern = re.compile(r"^(sk|rk)_(test|live)_", re.IGNORECASE)
    publishable_pattern = re.compile(r"^pk_(test|live)_", re.IGNORECASE)
    webhook_pattern = re.compile(r"^whsec_", re.IGNORECASE)

    updates = {}
    if req.stripe_secret_key is not None:
        cleaned = re.sub(r'[\s\u200b-\u200f\u2028-\u202f\u00a0]+', '', req.stripe_secret_key.strip())
        if not secret_pattern.match(cleaned):
            raise ValidationException("stripe_secret_key must start with sk_test_, sk_live_, rk_test_, or rk_live_")
        updates["stripe_secret_key"] = cleaned
    if req.stripe_public_key is not None:
        cleaned = re.sub(r'[\s\u200b-\u200f\u2028-\u202f\u00a0]+', '', req.stripe_public_key.strip())
        if not publishable_pattern.match(cleaned):
            raise ValidationException("stripe_public_key must start with pk_test_ or pk_live_")
        updates["stripe_public_key"] = cleaned
    if req.stripe_webhook_secret is not None:
        cleaned = re.sub(r'[\s\u200b-\u200f\u2028-\u202f\u00a0]+', '', req.stripe_webhook_secret.strip())
        if not webhook_pattern.match(cleaned):
            raise ValidationException("stripe_webhook_secret must start with whsec_")
        updates["stripe_webhook_secret"] = cleaned

    await _save_settings(db, updates)
    for key, val in updates.items():
        setattr(settings, key.upper(), val)
    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


# ── Razorpay Settings ──

@router.put("/settings/razorpay", response_model=SettingsDashboardResponse)
async def update_razorpay(
    req: RazorpaySettingsUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updates = {}
    if req.razorpay_key_id is not None:
        updates["razorpay_key_id"] = req.razorpay_key_id.strip()
    if req.razorpay_key_secret is not None:
        updates["razorpay_key_secret"] = req.razorpay_key_secret.strip()
    if req.razorpay_webhook_secret is not None:
        updates["razorpay_webhook_secret"] = req.razorpay_webhook_secret.strip()

    await _save_settings(db, updates)
    for key, val in updates.items():
        setattr(settings, key.upper(), val)
    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


# ── PayPal Settings ──

@router.put("/settings/paypal", response_model=SettingsDashboardResponse)
async def update_paypal(
    req: PaypalSettingsUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updates = {}
    if req.paypal_client_id is not None:
        updates["paypal_client_id"] = req.paypal_client_id.strip()
    if req.paypal_client_secret is not None:
        updates["paypal_client_secret"] = req.paypal_client_secret.strip()
    if req.paypal_webhook_id is not None:
        updates["paypal_webhook_id"] = req.paypal_webhook_id.strip()
    if req.paypal_mode is not None:
        mode = req.paypal_mode.strip().lower()
        if mode not in ("sandbox", "live"):
            raise ValidationException("paypal_mode must be 'sandbox' or 'live'")
        updates["paypal_mode"] = mode

    await _save_settings(db, updates)
    for key, val in updates.items():
        setattr(settings, key.upper(), val)
    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


# ── Helcim Settings ──

@router.put("/settings/helcim", response_model=SettingsDashboardResponse)
async def update_helcim(
    req: HelcimSettingsUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updates = {}
    if req.helcim_api_token is not None:
        updates["helcim_api_token"] = req.helcim_api_token.strip()
    if req.helcim_account_id is not None:
        updates["helcim_account_id"] = req.helcim_account_id.strip()
    if req.helcim_webhook_secret is not None:
        updates["helcim_webhook_secret"] = req.helcim_webhook_secret.strip()
    if req.helcim_mode is not None:
        mode = req.helcim_mode.strip().lower()
        if mode not in ("sandbox", "live"):
            raise ValidationException("helcim_mode must be 'sandbox' or 'live'")
        updates["helcim_mode"] = mode

    await _save_settings(db, updates)
    for key, val in updates.items():
        setattr(settings, key.upper(), val)
    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)


# ── Active Payment Processors ──

@router.put("/settings/active-processors", response_model=SettingsDashboardResponse)
async def update_active_processors(
    req: ActivePaymentProcessorsUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from schemas import ALLOWED_PAYMENT_PROCESSORS
    cleaned = []
    for p in req.active_payment_processors:
        p = p.strip().lower()
        if p not in ALLOWED_PAYMENT_PROCESSORS:
            raise ValidationException(f"Invalid payment processor '{p}'. Allowed: {', '.join(ALLOWED_PAYMENT_PROCESSORS)}")
        cleaned.append(p)

    value = ",".join(cleaned)
    await _save_settings(db, {"active_payment_processors": value})
    settings.ACTIVE_PAYMENT_PROCESSORS = value
    await db.flush()
    stored = await _get_all_stored(db)
    return _build_settings_response(stored)
