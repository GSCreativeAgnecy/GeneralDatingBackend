# Security Model

## Authentication Flow

1. User sends phone number → receives OTP via configured SMS provider
2. OTP verification → JWT access + refresh tokens issued
3. All protected endpoints require `Authorization: Bearer <access_token>`
4. Token types discriminated: `"type": "access"` vs `"type": "refresh"`

## Password Security

- **Algorithm**: bcrypt via passlib
- **Constraint**: `bcrypt<4.1` (pinned in requirements.txt)

## OTP Security

- 6-digit numeric codes (cryptographically random via `secrets.randbelow`)
- 300-second TTL (configurable)
- Rate limited: 3 requests per 10 minutes per phone
- Single-use: deleted after verification
- Bypass: `OTP_BYPASS` env var for development only
- Stored in `otp_records` table (not in memory)

## Authorization Levels

| Level | Dependency | Gate |
|-------|-----------|------|
| Public | None | Open endpoints |
| Authenticated | `get_current_user` | Valid Bearer token |
| Premium | `get_premium_user` | `is_premium == True` |
| Admin | `get_current_admin` | Phone in `ADMIN_PHONES` |

## Security Headers

Applied on every response:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

## CORS

- Configurable origins via `CORS_ORIGINS`
- Explicit methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
- Explicit headers: Authorization, Content-Type, Accept, Origin, X-Requested-With
- Credentials allowed
- Default (dev): localhost:3000, 5173, 8081

## Rate Limiting

- 100 requests per 60 seconds per IP
- Thread-safe with periodic stale entry cleanup
- Exemptions: `/api/v1/uploads`, `/ws`

## Request Size

- Maximum 10MB request body (configurable)

## Known Gaps

- No CSRF protection on form endpoints (login, checkout pages)
- No account lockout after repeated failed logins
- In-memory rate limiter (not suitable for multi-instance)
- No HSTS header in default config (add for production HTTPS)

## Production Checklist

- [ ] Set `JWT_SECRET` ≥ 64 random characters
- [ ] Set `ADMIN_PHONES` to real phone numbers
- [ ] Configure real SMS provider
- [ ] Set `CORS_ORIGINS` to explicit frontend domains
- [ ] Enable HTTPS + add `Strict-Transport-Security` header
- [ ] Set `DATABASE_ECHO=false`
- [ ] Change default DB credentials
- [ ] Run `pip-audit` or `safety check`
- [ ] Remove or regenerate seed admin account
