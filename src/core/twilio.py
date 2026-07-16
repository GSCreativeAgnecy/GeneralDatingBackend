from twilio.rest import Client
from core.config import settings


def _client() -> Client:
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_otp(phone: str, otp: str) -> bool:
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        return False
    try:
        msg = _client().messages.create(
            body=f"Your Brownies verification code is: {otp}",
            from_=settings.TWILIO_PHONE,
            to=phone,
        )
        return msg.sid is not None
    except Exception as e:
        print(f"[twilio] Failed to send OTP to {phone}: {e}")
        return False


def is_configured() -> bool:
    return bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_PHONE)
