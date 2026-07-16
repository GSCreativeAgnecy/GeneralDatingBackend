import asyncio
import hmac
import hashlib

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings

HELCIM_SANDBOX = "https://api.helcim.com/v2"
HELCIM_LIVE = "https://api.helcim.com/v2"


async def _get_api_token(db: AsyncSession) -> str:
    result = await db.execute(text("SELECT value FROM app_settings WHERE key = 'helcim_api_token'"))
    row = result.scalar_one_or_none()
    if row:
        return row
    if settings.HELCIM_API_TOKEN:
        return settings.HELCIM_API_TOKEN
    raise ValueError("Helcim API token is not configured")


async def _get_account_id(db: AsyncSession) -> str:
    result = await db.execute(text("SELECT value FROM app_settings WHERE key = 'helcim_account_id'"))
    row = result.scalar_one_or_none()
    if row:
        return row
    if settings.HELCIM_ACCOUNT_ID:
        return settings.HELCIM_ACCOUNT_ID
    raise ValueError("Helcim account ID is not configured")


async def _get_webhook_secret(db: AsyncSession) -> str:
    result = await db.execute(text("SELECT value FROM app_settings WHERE key = 'helcim_webhook_secret'"))
    row = result.scalar_one_or_none()
    if row:
        return row
    if settings.HELCIM_WEBHOOK_SECRET:
        return settings.HELCIM_WEBHOOK_SECRET
    return ""


async def _get_default_currency(db: AsyncSession) -> str:
    result = await db.execute(text("SELECT value FROM app_settings WHERE key = 'default_currency'"))
    row = result.scalar_one_or_none()
    if row:
        return str(row).upper()
    return settings.DEFAULT_CURRENCY.upper()


async def _headers(db: AsyncSession) -> dict:
    token = await _get_api_token(db)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _paisa_to_decimal(amount_paise: int) -> str:
    return f"{amount_paise / 100:.2f}"


async def create_checkout(
    db: AsyncSession,
    *,
    plan_name: str,
    amount_paise: int,
    user_id: int,
    plan_id: int,
    success_url: str,
    cancel_url: str,
) -> dict:
    account_id = await _get_account_id(db)
    currency = await _get_default_currency(db)
    hdrs = await _headers(db)

    payload = {
        "amount": float(_paisa_to_decimal(amount_paise)),
        "currency": currency,
        "amountShipping": 0,
        "amountTax": 0,
        "amountDiscount": 0,
        "paymentType": "purchase",
        "test": True,
        "customer": {
            "customerCode": f"user_{user_id}",
        },
        "metadata": {
            "plan_name": plan_name,
            "plan_id": str(plan_id),
            "user_id": str(user_id),
        },
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{HELCIM_SANDBOX}/helcimpay/initialize",
            json=payload,
            headers=hdrs,
            timeout=30,
        ) as resp:
            data = await resp.json()
            if resp.status not in (200, 201):
                raise ValueError(f"Helcim checkout creation failed: {data.get('responseMessage', resp.status)}")

            return {
                "checkout_token": data.get("checkoutToken", ""),
                "checkout_url": f"https://secure.myhelcim.com/checkout/{data.get('checkoutToken', '')}",
                "secret_token": data.get("secretToken", ""),
            }


async def verify_webhook(db: AsyncSession, payload: bytes, signature: str) -> dict:
    webhook_secret = await _get_webhook_secret(db)
    if not webhook_secret:
        return {}

    computed = hmac.new(
        webhook_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed, signature):
        raise ValueError("Invalid Helcim webhook signature")

    import json
    return json.loads(payload)


def is_configured(db_result: dict | None = None) -> bool:
    if db_result:
        return bool(db_result.get("helcim_api_token") and db_result.get("helcim_account_id"))
    return bool(settings.HELCIM_API_TOKEN and settings.HELCIM_ACCOUNT_ID)
