import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.auth_deps import get_current_user
from core.security import hash_password
from core.exceptions import NotFoundException, ValidationException, StripeIntegrationError
from core.razorpay import (
    create_order, verify_signature, verify_webhook_signature, fetch_payment,
)
from core.stripe import create_checkout_session, construct_webhook_event, mask_key
from core.paypal import create_order as paypal_create_order, capture_order as paypal_capture_order, verify_webhook as paypal_verify_webhook
from core.helcim import create_checkout as helcim_create_checkout, verify_webhook as helcim_verify_webhook
from models import User, Subscription, Plan
from schemas import SubscriptionOut, SubscriptionOrderOut, VerifyPaymentRequest, SuccessResponse

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/subscriptions", tags=["subscriptions"])


async def _activate(user_id: int, plan: Plan | None, payment_id: str, db: AsyncSession):
    duration = plan.duration_days if plan else 30
    plan_name = plan.name if plan else "premium_monthly"
    plan_id_val = plan.id if plan else None

    now = datetime.now(timezone.utc)
    start_from = now

    existing = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
            Subscription.ends_at > now,
        ).order_by(Subscription.ends_at.desc())
    )
    active_sub = existing.scalars().first()
    if active_sub and active_sub.ends_at:
        start_from = active_sub.ends_at

    sub = Subscription(
        user_id=user_id,
        plan_type=plan_name,
        plan_id=plan_id_val,
        payment_id=payment_id,
        starts_at=now,
        ends_at=start_from + timedelta(days=duration),
        is_active=True,
    )
    db.add(sub)
    await db.flush()

    old_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.id != sub.id,
            Subscription.is_active == True,
        )
    )
    for old in old_result.scalars().all():
        old.is_active = False

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.is_premium = True


@router.get("/plans")
async def get_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.sort_order))
    plans = []
    for p in result.scalars().all():
        plans.append({
            "id": str(p.id), "name": p.name, "price": p.price_paise, "duration_days": p.duration_days,
            "swipes_per_day": p.swipes_per_day,
            "super_likes_per_day": p.super_likes_per_day,
            "messages": p.messages,
            "see_who_liked_you": p.see_who_liked_you,
            "no_ads": p.no_ads,
            "read_receipts": p.read_receipts,
            "incognito_mode": p.incognito_mode,
            "verified_badge": p.verified_badge,
            "boosts_per_month": p.boosts_per_month,
            "max_profile_photos": p.max_profile_photos,
            "photos_in_inbox_per_day": p.photos_in_inbox_per_day,
        })
    return {"plans": plans}


@router.get("/me", response_model=SubscriptionOut)
async def get_my_subscription(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id, Subscription.is_active == True
        ).order_by(Subscription.ends_at.desc())
    )
    sub = result.scalars().first()
    if not sub:
        return SubscriptionOut(
            id=0, plan_type="free",
            starts_at=user.created_at or datetime.now(timezone.utc),
            ends_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            is_active=True,
        )
    return SubscriptionOut.model_validate(sub)


@router.post("/order", response_model=SubscriptionOrderOut)
async def create_subscription_order(
    plan_id: int = Query(..., description="Database plan ID"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id, Plan.is_active == True))
    plan = result.scalar_one_or_none()
    if not plan or plan.price_paise == 0:
        raise ValidationException("Invalid plan")

    receipt = f"rcpt_{user.id}_{datetime.now(timezone.utc).timestamp():.0f}"
    order = create_order(plan.price_paise, "INR", receipt)

    return SubscriptionOrderOut(
        order_id=order["id"],
        amount=plan.price_paise,
        currency=order.get("currency", "INR"),
        key_id=settings.RAZORPAY_KEY_ID,
    )


@router.post("/verify")
async def verify_payment(
    req: VerifyPaymentRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Idempotency: check for duplicate payment_id
    dup = await db.execute(
        select(Subscription).where(Subscription.payment_id == req.payment_id)
    )
    if dup.scalar_one_or_none():
        return SuccessResponse(message="Payment already processed")

    # Look up plan
    plan = None
    if req.plan_id:
        plan_result = await db.execute(select(Plan).where(Plan.id == req.plan_id))
        plan = plan_result.scalar_one_or_none()

    # Verify payment signature
    if settings.RAZORPAY_KEY_SECRET:
        if not verify_signature(req.order_id, req.payment_id, req.signature):
            raise ValidationException("Payment signature verification failed")

    # Confirm payment status from Razorpay
    payment = fetch_payment(req.payment_id)
    if payment and payment.get("status") != "captured":
        raise ValidationException(f"Payment not captured (status: {payment.get('status')})")

    await _activate(user.id, plan, req.payment_id, db)
    await db.flush()
    return SuccessResponse(message="Payment verified, premium activated")


# ── Stripe Checkout Session ──

@router.post("/checkout-session")
async def create_stripe_checkout_session(
    request: Request,
    plan_id: int = Query(..., description="Database plan ID"),
    success_url: str = Query(default=""),
    cancel_url: str = Query(default=""),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.is_active == True)
    )
    plan = result.scalar_one_or_none()
    if not plan or plan.price_paise == 0:
        raise ValidationException("Invalid plan")

    origin = ""
    if request and request.headers.get("origin"):
        origin = request.headers.get("origin", "")
    elif request and request.headers.get("referer"):
        from urllib.parse import urlparse
        parsed = urlparse(request.headers.get("referer", ""))
        origin = f"{parsed.scheme}://{parsed.netloc}"

    default_success = f"{origin}/checkout?success=true" if origin else f"{settings.API_V1_PREFIX}/subscriptions/success"
    default_cancel = f"{origin}/checkout?cancel=true" if origin else f"{settings.API_V1_PREFIX}/subscriptions/success"

    session = await create_checkout_session(
        db,
        plan_name=plan.name,
        amount_paise=plan.price_paise,
        user_id=user.id,
        plan_id=plan.id,
        success_url=success_url or default_success,
        cancel_url=cancel_url or default_cancel,
    )

    return {
        "checkout_url": session["checkout_url"],
        "session_id": session["session_id"],
    }


# ── Stripe Webhook ──

@router.post("/stripe-webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    if not signature:
        raise StripeIntegrationError("Missing stripe-signature header")

    try:
        event = await construct_webhook_event(db, payload, signature)
    except StripeIntegrationError:
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event.get("type", "")

    if event_type not in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        return {"status": "ignored", "event": event_type}

    session_obj = event.get("data", {}).get("object", {})

    payment_status = session_obj.get("payment_status", "")
    if payment_status != "paid":
        return {"status": "skipped", "reason": f"payment_status is '{payment_status}'"}

    metadata = session_obj.get("metadata", {})
    user_id_str = metadata.get("user_id", "")
    plan_id_str = metadata.get("plan_id", "")
    stripe_session_id = session_obj.get("id", "")

    if not user_id_str or not stripe_session_id:
        return {"status": "skipped", "reason": "missing user_id in session metadata"}

    user_id = int(user_id_str)

    dup = await db.execute(
        select(Subscription).where(Subscription.payment_id == stripe_session_id)
    )
    if dup.scalar_one_or_none():
        return {"status": "duplicate"}

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"status": "skipped", "reason": "user not found"}

    plan = None
    if plan_id_str:
        plan_result = await db.execute(select(Plan).where(Plan.id == int(plan_id_str)))
        plan = plan_result.scalar_one_or_none()

    await _activate(user_id, plan, stripe_session_id, db)
    await db.commit()
    return {"status": "ok"}


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    body_str = body.decode("utf-8")
    signature = request.headers.get("x-razorpay-signature", "")

    if settings.RAZORPAY_WEBHOOK_SECRET:
        if not verify_webhook_signature(body_str, signature):
            from core.exceptions import ForbiddenException
            raise ForbiddenException("Invalid webhook signature")

    event = json.loads(body_str)
    event_type = event.get("event", "")

    if event_type != "payment.captured":
        return {"status": "ignored"}

    payload = event.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = payload.get("id", "")
    notes = payload.get("notes", {})
    user_id_str = notes.get("user_id", "")
    plan_id_str = notes.get("plan_id", "")

    if not user_id_str or not payment_id:
        return {"status": "skipped", "reason": "missing user_id in notes"}

    user_id = int(user_id_str)

    # Idempotency
    dup = await db.execute(
        select(Subscription).where(Subscription.payment_id == payment_id)
    )
    if dup.scalar_one_or_none():
        return {"status": "duplicate"}

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"status": "skipped", "reason": "user not found"}

    plan = None
    if plan_id_str:
        plan_result = await db.execute(select(Plan).where(Plan.id == int(plan_id_str)))
        plan = plan_result.scalar_one_or_none()

    await _activate(user_id, plan, payment_id, db)
    await db.commit()
    return {"status": "ok"}


@router.post("/cancel")
async def cancel_subscription(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id, Subscription.is_active == True
        )
    )
    for sub in result.scalars().all():
        sub.is_active = False
    user.is_premium = False
    return SuccessResponse(message="Subscription cancelled")


# ── Web Checkout (no JWT, phone + OTP auth) ──

@router.post("/web-order")
async def create_web_order(
    plan_id: int = Query(...),
    phone_number: str = Query(...),
    otp: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    phone = phone_number.strip()
    if not phone or len(phone) < 10:
        raise ValidationException("Invalid phone number")

    from core.security import verify_otp_async
    if not await verify_otp_async(phone, otp, db):
        raise ValidationException("Invalid or expired OTP")

    result = await db.execute(select(Plan).where(Plan.id == plan_id, Plan.is_active == True, Plan.price_paise > 0))
    plan = result.scalar_one_or_none()
    if not plan:
        raise ValidationException("Invalid plan")

    receipt = f"web_{phone}_{datetime.now(timezone.utc).timestamp():.0f}"
    order = create_order(plan.price_paise, "INR", receipt)
    return {
        "order_id": order["id"],
        "amount": plan.price_paise,
        "currency": order.get("currency", "INR"),
        "key_id": settings.RAZORPAY_KEY_ID,
    }


@router.post("/web-verify")
async def verify_web_payment(
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await req.json()
    phone = (body.get("phone_number") or "").strip()
    order_id = body.get("order_id", "")
    payment_id = body.get("payment_id", "")
    signature = body.get("signature", "")
    plan_id = body.get("plan_id")

    if not phone or not order_id or not payment_id:
        raise ValidationException("Missing payment details")

    dup = await db.execute(select(Subscription).where(Subscription.payment_id == payment_id))
    if dup.scalar_one_or_none():
        return SuccessResponse(message="Payment already processed")

    result = await db.execute(select(User).where(User.phone_number == phone))
    user = result.scalar_one_or_none()
    if not user:
        user = User(phone_number=phone, phone_verified=True, password_hash=hash_password(phone), first_name="", date_of_birth="", gender="", city="")
        db.add(user)
        await db.flush()

    plan = None
    if plan_id:
        plan_result = await db.execute(select(Plan).where(Plan.id == int(plan_id)))
        plan = plan_result.scalar_one_or_none()

    if settings.RAZORPAY_KEY_SECRET:
        if not verify_signature(order_id, payment_id, signature):
            raise ValidationException("Payment verification failed")

    payment = fetch_payment(payment_id)
    if payment and payment.get("status") != "captured":
        raise ValidationException(f"Payment not captured")

    await _activate(user.id, plan, payment_id, db)
    await db.flush()
    return SuccessResponse(message="Payment verified, premium activated")


# ── PayPal Checkout ──

@router.post("/paypal-order")
async def create_paypal_order(
    request: Request,
    plan_id: int = Query(..., description="Database plan ID"),
    success_url: str = Query(default=""),
    cancel_url: str = Query(default=""),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.is_active == True)
    )
    plan = result.scalar_one_or_none()
    if not plan or plan.price_paise == 0:
        raise ValidationException("Invalid plan")

    origin = ""
    if request and request.headers.get("origin"):
        origin = request.headers.get("origin", "")
    elif request and request.headers.get("referer"):
        from urllib.parse import urlparse
        parsed = urlparse(request.headers.get("referer", ""))
        origin = f"{parsed.scheme}://{parsed.netloc}"

    default_success = f"{origin}/checkout?success=true" if origin else f"{settings.API_V1_PREFIX}/subscriptions/paypal-success"
    default_cancel = f"{origin}/checkout?cancel=true" if origin else f"{settings.API_V1_PREFIX}/subscriptions/paypal-cancel"

    order = await paypal_create_order(
        db,
        plan_name=plan.name,
        amount_paise=plan.price_paise,
        user_id=user.id,
        plan_id=plan.id,
        success_url=success_url or default_success,
        cancel_url=cancel_url or default_cancel,
    )

    return {
        "order_id": order["order_id"],
        "approval_url": order.get("approval_url"),
        "status": order.get("status", "CREATED"),
    }


@router.post("/paypal-capture")
async def capture_paypal_order(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()
    paypal_order_id = body.get("order_id", "")
    plan_id_str = body.get("plan_id")

    if not paypal_order_id:
        raise ValidationException("Missing PayPal order ID")

    user_id_str = str(body.get("user_id", ""))
    payment_id = f"paypal_{paypal_order_id}"

    dup = await db.execute(
        select(Subscription).where(Subscription.payment_id == payment_id)
    )
    if dup.scalar_one_or_none():
        return SuccessResponse(message="Payment already processed")

    capture_data = await paypal_capture_order(db, paypal_order_id)
    status = capture_data.get("status", "")

    if status != "COMPLETED":
        raise ValidationException(f"PayPal payment not completed (status: {status})")

    user_id = int(user_id_str)
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise ValidationException("User not found")

    plan = None
    if plan_id_str:
        plan_result = await db.execute(select(Plan).where(Plan.id == int(plan_id_str)))
        plan = plan_result.scalar_one_or_none()

    await _activate(user_id, plan, payment_id, db)
    await db.commit()
    return SuccessResponse(message="PayPal payment captured, premium activated")


@router.post("/paypal-webhook")
async def paypal_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    body_str = body.decode("utf-8")

    headers = {
        "paypal-transmission-id": request.headers.get("paypal-transmission-id", ""),
        "paypal-transmission-time": request.headers.get("paypal-transmission-time", ""),
        "paypal-cert-url": request.headers.get("paypal-cert-url", ""),
        "paypal-auth-algo": request.headers.get("paypal-auth-algo", ""),
        "paypal-transmission-sig": request.headers.get("paypal-transmission-sig", ""),
    }

    try:
        event = await paypal_verify_webhook(db, body_str, headers)
    except Exception:
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if not event:
        return {"status": "ok", "message": "Webhook verification skipped (no webhook ID configured)"}

    event_type = event.get("event_type", "")

    if event_type != "PAYMENT.CAPTURE.COMPLETED":
        return {"status": "ignored", "event": event_type}

    resource = event.get("resource", {})
    paypal_order_id = resource.get("id", "")
    payment_id = f"paypal_{paypal_order_id}"

    dup = await db.execute(
        select(Subscription).where(Subscription.payment_id == payment_id)
    )
    if dup.scalar_one_or_none():
        return {"status": "duplicate"}

    custom_id = resource.get("custom_id", "")
    parts = custom_id.split("_")
    user_id = None
    plan_id = None
    if len(parts) >= 2:
        try:
            user_id = int(parts[-1])
        except ValueError:
            pass

    if not user_id:
        return {"status": "skipped", "reason": "missing user_id in custom_id"}

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"status": "skipped", "reason": "user not found"}

    plan = None
    await _activate(user_id, plan, payment_id, db)
    await db.commit()
    return {"status": "ok"}


# ── Helcim Checkout ──

@router.post("/helcim-checkout")
async def create_helcim_checkout(
    request: Request,
    plan_id: int = Query(..., description="Database plan ID"),
    success_url: str = Query(default=""),
    cancel_url: str = Query(default=""),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.is_active == True)
    )
    plan = result.scalar_one_or_none()
    if not plan or plan.price_paise == 0:
        raise ValidationException("Invalid plan")

    origin = ""
    if request and request.headers.get("origin"):
        origin = request.headers.get("origin", "")

    default_success = f"{origin}/checkout?success=true" if origin else f"{settings.API_V1_PREFIX}/subscriptions/success"
    default_cancel = f"{origin}/checkout?cancel=true" if origin else f"{settings.API_V1_PREFIX}/subscriptions/success"

    checkout_data = await helcim_create_checkout(
        db,
        plan_name=plan.name,
        amount_paise=plan.price_paise,
        user_id=user.id,
        plan_id=plan.id,
        success_url=success_url or default_success,
        cancel_url=cancel_url or default_cancel,
    )

    return {
        "checkout_token": checkout_data["checkout_token"],
        "checkout_url": checkout_data["checkout_url"],
    }


@router.post("/helcim-webhook")
async def helcim_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    signature = request.headers.get("x-helcim-signature", "")

    try:
        event = await helcim_verify_webhook(db, payload, signature)
    except Exception:
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if not event:
        return {"status": "ok", "message": "Webhook verification skipped (no webhook secret configured)"}

    event_type = event.get("event", "")

    if event_type not in ("PAYMENT_SUCCESS", "payment.success"):
        return {"status": "ignored", "event": event_type}

    metadata = event.get("metadata", {})
    user_id_str = str(metadata.get("user_id", ""))
    plan_id_str = str(metadata.get("plan_id", ""))
    transaction_id = event.get("transactionId", event.get("id", ""))

    payment_id = f"helcim_{transaction_id}"

    if not user_id_str:
        return {"status": "skipped", "reason": "missing user_id in metadata"}

    dup = await db.execute(
        select(Subscription).where(Subscription.payment_id == payment_id)
    )
    if dup.scalar_one_or_none():
        return {"status": "duplicate"}

    user_id = int(user_id_str)
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"status": "skipped", "reason": "user not found"}

    plan = None
    if plan_id_str:
        plan_result = await db.execute(select(Plan).where(Plan.id == int(plan_id_str)))
        plan = plan_result.scalar_one_or_none()

    await _activate(user_id, plan, payment_id, db)
    await db.commit()
    return {"status": "ok"}
