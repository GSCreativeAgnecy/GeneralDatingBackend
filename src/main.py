from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError

from core.config import settings
from core.database import async_session, engine, init_db
from middleware.rate_limit import RateLimitMiddleware
from models import WaitlistSubscriber
from routers import (
    admin,
    auth,
    discovery,
    family,
    internal_docs,
    matches,
    notifications,
    preferences,
    profile,
    profile_v2,
    reports,
    subscriptions,
    verification,
)
from websocket.handler import router as ws_router

_SETTING_KEYS = {
    "max_photos_per_user",
    "max_photo_size_mb",
    "family_share_expire_days",
    "app_name",
    "primary_color",
    "secondary_color",
    "accent_color",
    "logo_url",
    "default_currency",
    "active_payment_processors",
    "stripe_secret_key",
    "stripe_public_key",
    "stripe_webhook_secret",
    "razorpay_key_id",
    "razorpay_key_secret",
    "razorpay_webhook_secret",
    "paypal_client_id",
    "paypal_client_secret",
    "paypal_webhook_id",
    "paypal_mode",
    "helcim_api_token",
    "helcim_account_id",
    "helcim_webhook_secret",
    "helcim_mode",
    "preferred_otp_provider",
    "twilio_account_sid",
    "twilio_auth_token",
    "twilio_phone",
    "android_sms_gateway_url",
    "android_sms_gateway_api_key",
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "smtp_password",
    "smtp_from_name",
    "notify_email",
}


async def load_runtime_settings() -> None:
    async with engine.connect() as conn:
        try:
            result = await conn.execute(text("SELECT key, value FROM app_settings"))
            rows = result.fetchall()
        except ProgrammingError:
            return

    for key, val in rows:
        key = str(key).strip().lower()
        if key not in _SETTING_KEYS:
            continue
        val_str = str(val)

        int_keys = {
            "max_photos_per_user", "max_photo_size_mb",
            "family_share_expire_days", "smtp_port",
        }
        if key in int_keys:
            try:
                setattr(settings, key.upper(), int(val_str))
            except (ValueError, TypeError):
                pass
        elif key == "default_currency":
            settings.DEFAULT_CURRENCY = val_str.upper()
        else:
            setattr(settings, key.upper(), val_str)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await load_runtime_settings()
    app.title = settings.APP_NAME
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    expose_headers=["Retry-After", "Content-Disposition"],
    max_age=600,
)

app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

max_request_size = 10 * 1024 * 1024


@app.middleware("http")
async def request_size_limit_middleware(request: Request, call_next):
    if request.headers.get("content-length"):
        content_length = int(request.headers["content-length"])
        if content_length > max_request_size:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"},
            )
    return await call_next(request)


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(profile_v2.router)
app.include_router(discovery.router)
app.include_router(matches.router)
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(family.router)
app.include_router(verification.router)
app.include_router(preferences.router)
app.include_router(subscriptions.router)
app.include_router(admin.router)
app.include_router(internal_docs.router)
app.include_router(ws_router, prefix=settings.API_V1_PREFIX)

upload_dir = settings.UPLOAD_DIR
upload_dir.mkdir(parents=True, exist_ok=True)
(upload_dir / "photos").mkdir(parents=True, exist_ok=True)
(upload_dir / "verification").mkdir(parents=True, exist_ok=True)
(upload_dir / "logos").mkdir(parents=True, exist_ok=True)
app.mount("/api/v1/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

if Path("static/login").exists():
    app.mount("/login", StaticFiles(directory="static/login", html=True), name="login")

if Path("static/checkout").exists():
    app.mount("/checkout", StaticFiles(directory="static/checkout", html=True), name="checkout")

if Path("static/admin").exists():
    app.mount("/admin", StaticFiles(directory="static/admin", html=True), name="admin")


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/api/v1/branding")
async def get_branding():
    return {
        "app_name": settings.APP_NAME,
        "primary_color": settings.PRIMARY_COLOR,
        "secondary_color": settings.SECONDARY_COLOR,
        "accent_color": settings.ACCENT_COLOR,
        "logo_url": settings.LOGO_URL,
    }


class SubscribeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.post("/api/subscribe")
async def subscribe(req: SubscribeRequest):
    from core.mail import notify_new_subscriber

    async with async_session() as db:
        result = await db.execute(
            select(WaitlistSubscriber).where(WaitlistSubscriber.email == req.email)
        )
        if result.scalar_one_or_none():
            return {"success": True, "message": "You're already on the list!"}

        db.add(WaitlistSubscriber(name=req.name, email=req.email))
        await db.commit()

    notify_new_subscriber(req.name, req.email)

    return {"success": True, "message": "You're on the list!"}


landing_path = Path("static/landing/index.html")
if landing_path.exists():
    @app.get("/coming-soon", response_class=HTMLResponse)
    async def landing():
        return landing_path.read_text(encoding="utf-8")
