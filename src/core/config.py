from __future__ import annotations

import os
import secrets
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    APP_NAME: str = "Ardhang Matrimony"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    PRIMARY_COLOR: str = "#6B3F2E"
    SECONDARY_COLOR: str = "#4A2C20"
    ACCENT_COLOR: str = "#D4A358"
    DEFAULT_CURRENCY: str = "INR"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/appointment"
    DATABASE_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600

    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    OTP_BYPASS: str = ""
    OTP_LENGTH: int = 6
    OTP_EXPIRE_SECONDS: int = 300
    OTP_RATE_LIMIT: int = 3
    OTP_RATE_WINDOW_MINUTES: int = 10

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE: str = ""
    ANDROID_SMS_GATEWAY_URL: str = ""
    ANDROID_SMS_GATEWAY_API_KEY: str = ""
    PREFERRED_OTP_PROVIDER: str = ""

    UPLOAD_DIR: Path = Path("data/uploads")
    MAX_PHOTO_SIZE_MB: int = 10
    MAX_PHOTOS_PER_USER: int = 6

    DAILY_LIKES_FREE: int = 50
    DAILY_SUPER_LIKES_FREE: int = 1

    FAMILY_SHARE_EXPIRE_DAYS: int = 7
    FAMILY_SHARE_TOKEN_LENGTH: int = 32

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Ardhang Matrimony"
    NOTIFY_EMAIL: str = ""

    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLIC_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_WEBHOOK_ID: str = ""
    PAYPAL_MODE: str = "sandbox"

    HELCIM_API_TOKEN: str = ""
    HELCIM_ACCOUNT_ID: str = ""
    HELCIM_WEBHOOK_SECRET: str = ""
    HELCIM_MODE: str = "sandbox"

    ACTIVE_PAYMENT_PROCESSORS: str = ""

    ADMIN_PHONES: str = "0000000000"
    CORS_ORIGINS: str = ""

    ENABLE_INTERNAL_DOCS: bool = False

    @field_validator("JWT_SECRET", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if isinstance(v, str) and v.strip():
            stripped = v.strip()
            if len(stripped) < 32:
                raise ValueError(
                    "JWT_SECRET must be at least 32 characters for security. "
                    "Use: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            return stripped
        import secrets
        import sys
        generated = secrets.token_urlsafe(64)
        print(
            f"\n*** WARNING: JWT_SECRET not set. Auto-generated: {generated} ***\n"
            "*** Set JWT_SECRET in your environment for production use.    ***\n",
            file=sys.stderr,
        )
        return generated

    @property
    def admin_phones_list(self) -> list[str]:
        return [p.strip() for p in self.ADMIN_PHONES.split(",") if p.strip() if p]

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.CORS_ORIGINS.strip():
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8081",
            ]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def jwt_secret(self) -> str:
        return self.JWT_SECRET


settings = Settings()
