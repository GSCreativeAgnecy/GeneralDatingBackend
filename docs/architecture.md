# Architecture

## System Overview

Ardhang Matrimony is a monolithic FastAPI backend with modular architecture. It serves REST and WebSocket APIs for a matchmaking application targeting the Indian market.

```
┌──────────────────────────────────────────────────────────┐
│                    Client Layer                          │
│  Mobile App  │  Web Browser  │  Admin Dashboard  │  Webhooks │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│                  FastAPI Application                     │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Middleware│ │   Routers    │ │  Core Infrastructure │ │
│  │  - CORS  │ │  - auth      │ │  - Security / JWT    │ │
│  │  - Rate  │ │  - profile   │ │  - Auth Dependencies │ │
│  │  - Size  │ │  - discovery │ │  - File Uploads      │ │
│  │  - Sec   │ │  - matches   │ │  - Payment Clients   │ │
│  │          │ │  - messages  │ │  - Email / Geo       │ │
│  │          │ │  - admin     │ │                      │ │
│  │          │ │  - profile_v2│ │                      │ │
│  └──────────┘ └──────────────┘ └──────────────────────┘ │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│                   Data Layer                             │
│  SQLAlchemy ORM → asyncpg → PostgreSQL 16               │
│  File System ← aiofiles (photos, verification)          │
└──────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI 0.109+ |
| Python | 3.12 |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 (async) |
| Driver | asyncpg |
| Auth | JWT (HS256) + bcrypt |
| OTP | Twilio / Android SMS Gateway |
| Payments | Stripe, Razorpay, PayPal, Helcim |
| WebSocket | Starlette native |
| Container | Docker + Docker Compose |

## Request Flow

1. Client sends request → CORS middleware validates origin
2. Rate limit middleware checks IP quota
3. Security headers middleware adds protections
4. Router matches endpoint by prefix
5. Dependencies resolve (`get_db` → session, `get_current_user` → auth)
6. Endpoint handler executes business logic
7. Response serialized through Pydantic models
8. Session commits (or rolls back on error)

## Key Design Decisions

- **Hybrid profile system**: Core identity in `users` table, extended profile in modular EAV tables with lookup tables for standardized values
- **In-memory caches**: Field definitions and rate limits cached per-process (suitable for single-instance, migrate to Redis for multi-instance)
- **Auto-migration**: `init_db()` creates tables and adds missing columns on startup
- **No service layer** (currently): Business logic lives in router handlers; `services/` directory exists for future extraction
- **Payment gateway abstraction**: Unified `_activate()` function supports all four processors

## Directory Structure

```
src/
├── main.py              # App entry point, middleware, mounts
├── seed.py              # DB seeder (admin, plans, profile sections)
├── core/                # Configuration, database, security, auth
├── models/              # SQLAlchemy ORM models (__init__.py + profile.py)
├── schemas/             # Pydantic request/response models
├── services/            # Business logic layer (profile_v2.py)
├── middleware/           # Rate limiting
├── routers/             # FastAPI APIRouter endpoints
├── websocket/           # WebSocket connection handler
├── templates/           # Jinja2 templates (for docs)
└── static/              # Static HTML pages (landing, login, admin)
```
