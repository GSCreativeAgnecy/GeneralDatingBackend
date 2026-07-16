import aiohttp
from core.config import settings


async def send_otp(phone: str, otp: str) -> bool:
    url = settings.ANDROID_SMS_GATEWAY_URL
    api_key = settings.ANDROID_SMS_GATEWAY_API_KEY
    if not url:
        return False

    payload = {
        "phoneNumber": phone,
        "message": f"Your Brownies verification code is: {otp}",
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=15) as resp:
                if resp.status < 400:
                    return True
                text = await resp.text()
                print(f"[android_sms] Gateway returned {resp.status}: {text[:200]}")
                return False
    except Exception as e:
        print(f"[android_sms] Failed to send OTP to {phone}: {e}")
        return False


def is_configured() -> bool:
    return bool(settings.ANDROID_SMS_GATEWAY_URL)
