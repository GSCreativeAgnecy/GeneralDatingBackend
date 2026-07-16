import asyncio
from datetime import datetime, timezone

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings

PAYPAL_SANDBOX = "https://api-m.sandbox.paypal.com"
PAYPAL_LIVE = "https://api-m.paypal.com"


async def _get_base_url(db: AsyncSession) -> str:
    result = await db.execute(text("SELECT value FROM app_settings WHERE key = 'paypal_mode'"))
    row = result.scalar_one_or_none()
    mode = (row or settings.PAYPAL_MODE or "sandbox").strip().lower()
    return PAYPAL_LIVE if mode == "live" else PAYPAL_SANDBOX


async def _get_client_id(db: AsyncSession) -> str:
    result = await db.execute(text("SELECT value FROM app_settings WHERE key = 'paypal_client_id'"))
    row = result.scalar_one_or_none()
    if row:
        return row
    if settings.PAYPAL_CLIENT_ID:
        return settings.PAYPAL_CLIENT_ID
    raise ValueError("PayPal client ID is not configured")


async def _get_client_secret(db: AsyncSession) -> str:
    result = await db.execute(text("SELECT value FROM app_settings WHERE key = 'paypal_client_secret'"))
    row = result.scalar_one_or_none()
    if row:
        return row
    if settings.PAYPAL_CLIENT_SECRET:
        return settings.PAYPAL_CLIENT_SECRET
    raise ValueError("PayPal client secret is not configured")


async def _get_webhook_id(db: AsyncSession) -> str:
    result = await db.execute(text("SELECT value FROM app_settings WHERE key = 'paypal_webhook_id'"))
    row = result.scalar_one_or_none()
    if row:
        return row
    if settings.PAYPAL_WEBHOOK_ID:
        return settings.PAYPAL_WEBHOOK_ID
    return ""


async def _get_access_token(db: AsyncSession) -> str:
    base_url = await _get_base_url(db)
    client_id = await _get_client_id(db)
    client_secret = await _get_client_secret(db)

    async with aiohttp.ClientSession() as session:
        auth = aiohttp.BasicAuth(client_id, client_secret)
        async with session.post(
            f"{base_url}/v1/oauth2/token",
            data="grant_type=client_credentials",
            auth=auth,
            headers={"Accept": "application/json"},
            timeout=15,
        ) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise ValueError(f"PayPal auth failed: {data.get('error_description', resp.status)}")
            return data["access_token"]


async def _get_default_currency(db: AsyncSession) -> str:
    result = await db.execute(text("SELECT value FROM app_settings WHERE key = 'default_currency'"))
    row = result.scalar_one_or_none()
    if row:
        return str(row).upper()
    return settings.DEFAULT_CURRENCY.upper()


def _paisa_to_decimal(amount_paise: int) -> str:
    return f"{amount_paise / 100:.2f}"


async def create_order(
    db: AsyncSession,
    *,
    plan_name: str,
    amount_paise: int,
    user_id: int,
    plan_id: int,
    success_url: str,
    cancel_url: str,
) -> dict:
    base_url = await _get_base_url(db)
    token = await _get_access_token(db)
    currency = await _get_default_currency(db)

    order_payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": f"plan_{plan_id}_user_{user_id}",
            "description": plan_name,
            "amount": {
                "currency_code": currency,
                "value": _paisa_to_decimal(amount_paise),
            },
        }],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                    "landing_page": "LOGIN",
                    "user_action": "PAY_NOW",
                    "return_url": success_url,
                    "cancel_url": cancel_url,
                }
            }
        },
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/v2/checkout/orders",
            json=order_payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        ) as resp:
            data = await resp.json()
            if resp.status not in (200, 201):
                raise ValueError(f"PayPal order creation failed: {data.get('message', resp.status)}")

            order_id = data["id"]
            approval_url = None
            for link in data.get("links", []):
                if link.get("rel") == "payer-action":
                    approval_url = link["href"]
                    break

            return {
                "order_id": order_id,
                "approval_url": approval_url,
                "status": data.get("status", "CREATED"),
            }


async def capture_order(db: AsyncSession, paypal_order_id: str) -> dict:
    base_url = await _get_base_url(db)
    token = await _get_access_token(db)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/v2/checkout/orders/{paypal_order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        ) as resp:
            data = await resp.json()
            if resp.status not in (200, 201):
                raise ValueError(f"PayPal capture failed: {data.get('message', resp.status)}")
            return data


async def verify_webhook(
    db: AsyncSession,
    body: str,
    headers: dict,
) -> dict:
    webhook_id = await _get_webhook_id(db)
    if not webhook_id:
        return {}

    base_url = await _get_base_url(db)
    token = await _get_access_token(db)

    verify_payload = {
        "transmission_id": headers.get("paypal-transmission-id", ""),
        "transmission_time": headers.get("paypal-transmission-time", ""),
        "cert_url": headers.get("paypal-cert-url", ""),
        "auth_algo": headers.get("paypal-auth-algo", ""),
        "transmission_sig": headers.get("paypal-transmission-sig", ""),
        "webhook_id": webhook_id,
        "webhook_event": body,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/v1/notifications/verify-webhook-signature",
            json=verify_payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15,
        ) as resp:
            data = await resp.json()
            if data.get("verification_status") == "SUCCESS":
                import json
                return json.loads(body) if isinstance(body, str) else body
            return {}


def is_configured(db_result: dict | None = None) -> bool:
    if db_result:
        return bool(db_result.get("paypal_client_id"))
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)
