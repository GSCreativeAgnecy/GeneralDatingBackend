import asyncio

import stripe
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import StripeIntegrationError


async def _get_secret_key(db: AsyncSession) -> str:
    """Read the active Stripe secret key from the database AppSettings table."""
    result = await db.execute(
        text("SELECT value FROM app_settings WHERE key = 'stripe_secret_key'")
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    if settings.STRIPE_SECRET_KEY:
        return settings.STRIPE_SECRET_KEY
    raise StripeIntegrationError("Stripe secret key is not configured")


async def _get_webhook_secret(db: AsyncSession) -> str:
    """Read the active Stripe webhook secret from the database AppSettings table."""
    result = await db.execute(
        text("SELECT value FROM app_settings WHERE key = 'stripe_webhook_secret'")
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    if settings.STRIPE_WEBHOOK_SECRET:
        return settings.STRIPE_WEBHOOK_SECRET
    raise StripeIntegrationError("Stripe webhook secret is not configured")


async def _get_default_currency(db: AsyncSession) -> str:
    """Read the active default currency from the database AppSettings table."""
    result = await db.execute(
        text("SELECT value FROM app_settings WHERE key = 'default_currency'")
    )
    row = result.scalar_one_or_none()
    if row:
        return str(row).upper()
    return settings.DEFAULT_CURRENCY.upper()


async def create_checkout_session(
    db: AsyncSession,
    *,
    plan_name: str,
    amount_paise: int,
    user_id: int,
    plan_id: int,
    success_url: str,
    cancel_url: str,
) -> dict:
    """
    Create a Stripe Checkout Session with automatic payment method detection
    (cards, Google Pay, Link, UPI, etc. as enabled in Stripe Dashboard).

    Uses ``mode: "payment"`` for one-time transactions.
    Amount is in the smallest currency unit (paise for INR, cents for USD, etc.).
    The currency is read dynamically from the DB ``default_currency`` setting.
    """
    secret_key = await _get_secret_key(db)
    currency = await _get_default_currency(db)

    params = {
        "mode": "payment",
        "line_items": [{
            "price_data": {
                "currency": currency.lower(),
                "product_data": {
                    "name": plan_name,
                },
                "unit_amount": amount_paise,
            },
            "quantity": 1,
        }],
        "metadata": {
            "user_id": str(user_id),
            "plan_id": str(plan_id),
        },
        "success_url": success_url,
        "cancel_url": cancel_url,
    }

    loop = asyncio.get_running_loop()
    try:
        session = await loop.run_in_executor(
            None,
            lambda: _create_session_sync(secret_key, params),
        )
        return {
            "checkout_url": session.url,
            "session_id": session.id,
        }
    except stripe.StripeError as exc:
        raise StripeIntegrationError(
            f"Failed to create checkout session: {getattr(exc, 'user_message', str(exc))}"
        )


def _create_session_sync(secret_key: str, params: dict) -> stripe.checkout.Session:
    stripe.api_key = secret_key
    return stripe.checkout.Session.create(**params)


async def construct_webhook_event(
    db: AsyncSession,
    payload: bytes,
    signature: str,
) -> stripe.Event:
    """
    Validate a Stripe webhook signature and return the parsed Event.

    Runs signature verification in a thread-pool executor to avoid blocking
    the async event loop.
    """
    webhook_secret = await _get_webhook_secret(db)

    loop = asyncio.get_running_loop()
    try:
        event = await loop.run_in_executor(
            None,
            _verify_webhook_sync,
            payload,
            signature,
            webhook_secret,
        )
        return event
    except ValueError:
        raise StripeIntegrationError("Invalid webhook payload")
    except stripe.SignatureVerificationError:
        raise StripeIntegrationError("Invalid webhook signature")


def _verify_webhook_sync(payload: bytes, signature: str, secret: str) -> stripe.Event:
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=secret,
    )


def mask_key(key: str) -> str:
    """Return a masked representation of a secret key for safe display in admin UI."""
    if not key:
        return ""
    if len(key) <= 8:
        return key[:2] + "X" * (len(key) - 2)
    return key[:7] + "X" * (len(key) - 11) + key[-4:]
