# Authentication API

## Overview

Authentication uses phone-number-based OTP as the primary gateway, with email/password login as a secondary path. JWT access and refresh tokens secure all authenticated endpoints.

| Token Type | Default TTL | Config |
|-----------|-------------|--------|
| Access Token | 60 minutes | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh Token | 30 days | `REFRESH_TOKEN_EXPIRE_DAYS` |

## Endpoints

### POST `/auth/send-otp`

Send OTP to a phone number.

```json
// Request
{"phone_number": "9990000000"}

// Response
{
    "success": true,
    "retry_after_seconds": 30,
    "expires_in_seconds": 300
}
```

**Rate limit**: 3 requests per 10 minutes per phone number.

### POST `/auth/verify-otp`

Verify OTP and receive tokens. Creates user account on first login.

```json
// Request
{"phone_number": "9990000000", "otp": "123456"}

// Response
{
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "is_new_user": false,
    "profile_complete": true
}
```

### POST `/auth/login`

Login with phone/email + password.

### POST `/auth/register`

Register with email + password.

### POST `/auth/refresh`

Rotate tokens using refresh token.

### DELETE `/auth/account`

Permanently delete authenticated user's account.

## JWT Payload

```json
{
    "sub": "123",
    "exp": 1700000000,
    "type": "access"
}
```

Algorithm: HS256. Token type discriminates access from refresh tokens.

## OTP Providers

Configure via `PREFERRED_OTP_PROVIDER`:

- `twilio` — SMS via Twilio API
- `android_sms_gateway` — On-premise Android SMS gateway

Without a provider, OTPs are only visible in the API response when `DEBUG=true`.
