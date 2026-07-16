import razorpay
from core.config import settings


def _client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_order(amount_paise: int, currency: str = "INR", receipt: str = "") -> dict:
    if not settings.RAZORPAY_KEY_ID:
        return {
            "id": f"order_fake_{receipt}",
            "amount": amount_paise,
            "currency": currency,
            "status": "created",
        }
    return _client().order.create({
        "amount": amount_paise,
        "currency": currency,
        "receipt": receipt or f"rcpt_{amount_paise}",
    })


def verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    if not settings.RAZORPAY_KEY_SECRET:
        return True
    try:
        _client().utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False


def verify_webhook_signature(body: str, signature: str) -> bool:
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        return False
    try:
        _client().utility.verify_webhook_signature(body, signature, settings.RAZORPAY_WEBHOOK_SECRET)
        return True
    except razorpay.errors.SignatureVerificationError:
        return False


def fetch_payment(payment_id: str) -> dict | None:
    if not settings.RAZORPAY_KEY_ID:
        return {"id": payment_id, "status": "captured", "order_id": "order_fake"}
    try:
        return _client().payment.fetch(payment_id)
    except Exception:
        return None


def get_key_id() -> str:
    return settings.RAZORPAY_KEY_ID


def is_configured() -> bool:
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
