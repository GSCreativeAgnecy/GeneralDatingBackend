# Deployment Guide

## Docker Deployment (Recommended)

```yaml
# docker-compose.yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]

  api:
    build: .
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      JWT_SECRET: ${JWT_SECRET}
    volumes:
      - uploads:/app/data/uploads
    healthcheck:
      test: ["CMD", "python", "-c", "from urllib.request import urlopen; urlopen('http://localhost:8000/api/v1/health')"]

volumes:
  pgdata:
  uploads:
```

## Environment Variables

All configuration through environment variables. See `.env.example` for the full list.

### Critical (Required in Production)

```
JWT_SECRET=<64+ char random string>
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
ADMIN_PHONES=+9199XXXXXXXX,+9198XXXXXXXX
CORS_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com
```

### Optional

```
PREFERRED_OTP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=...
RAZORPAY_KEY_ID=...
SMTP_HOST=...
ENABLE_INTERNAL_DOCS=false
```

## Scaling

### Single Instance (Current)

The application is designed for single-instance deployment. All caches (rate limiter, profile field definitions) are in-memory.

### Multi-Instance (Future)

For horizontal scaling:
1. Replace in-memory rate limiter with Redis-based implementation
2. Add sticky sessions or Redis pub/sub for WebSocket fanout
3. Use centralized cache (Redis) for profile field definitions
4. Offload CPU-bound work (bcrypt, file processing) to background workers

## Database

- **PostgreSQL 16** with asyncpg driver
- Connection pool: 20 base, 10 overflow
- Auto-migration on startup via `init_db()`
- Manual SQL migrations in `migrations/` directory

## Health Checks

- **Docker healthcheck**: `GET /api/v1/health` every 30 seconds
- Returns `{"status": "ok", "app": "Ardhang Matrimony"}`
