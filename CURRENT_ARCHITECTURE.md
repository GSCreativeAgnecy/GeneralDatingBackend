# Brownies Backend — Current Architecture

> **Generated:** 2026-07-12
> **Codebase:** `src/`, `tests/`, `migrations/`, `assets/`
> **Python:** 3.12 | **Framework:** FastAPI | **Database:** PostgreSQL 16 + SQLAlchemy (async)

---

## 1. Executive Summary

**Purpose:** Brownies is an Indian dating application ("Dating, Desi Style"). The backend provides REST and WebSocket APIs for user authentication, profile management, swipe-based discovery, matching, in-app messaging, premium subscriptions, family/friend profile sharing, and administrative operations.

**Primary business domain:** Dating/matchmaking targeted at the Indian market, with features such as intent-based matching, caste/religion/earnings filters, women-first messaging, family-vetted profile sharing, and multi-language support.

**Major capabilities:**
- Phone-based OTP authentication + email/password registration
- Discovery feed with preference-based filtering (age, gender, distance, intent, city)
- Swipe mechanics (like, pass, super_like) with daily rate limits
- Mutual matching with notification generation
- In-app messaging with women-first message gate
- WebSocket connections for typing indicators and keepalive
- Premium subscriptions via Razorpay (INR payments)
- Family/friend profile sharing with time-limited access tokens
- Photo upload and verification
- Admin dashboard (users, matches, chats, reports, plans, limits, waitlist, stats)
- Landing page with waitlist signup

**Architectural style:** Monolithic modular backend — FastAPI application with flat routing (no versioned module nesting), SQLAlchemy async ORM, direct dependency injection via `Depends()`, and no separate service/repository layers. Business logic lives directly in router handlers.

**Approximate project size:** ~3,500 lines of Python across ~20 files (routers, models, schemas, core), plus ~1,500 lines of SQL migrations and ~2,500 lines of static HTML/CSS/JS for admin/landing/checkout/login pages.

**Overall maturity:** Early-stage/startup. The code is functional but lacks separation of concerns (no service layer, no repository layer). The `services/` directory exists but is empty. Authentication and core mechanics are solid. Observability (logging, metrics, tracing) is minimal.

---

## 2. Repository Structure

```
/
├── .gitignore                  # Standard Python gitignore
├── Dockerfile                  # Python 3.12-slim container
├── docker-compose.yaml         # PostgreSQL 16 + app service
├── entrypoint.sh               # Runs seed.py then uvicorn
├── pytest.ini                  # Test config (asyncio auto)
├── README.md                   # Minimal (title only)
├── requirements.txt            # 19 dependencies
├── user_data_fields.csv        # Data model reference spreadsheet
├── CURRENT_ARCHITECTURE.md     # This document
├── assets/
│   ├── Brownies-Logo.png
│   └── Intor-app-video.mp4
├── migrations/
│   └── 001_add_performance_indexes.sql
├── src/
│   ├── main.py                 # App entry point
│   ├── seed.py                 # DB seeder (admin user + default plans)
│   ├── generate_dummy_data.py  # Dummy data generator (SSE streaming)
│   ├── female_names_data.py    # Female name dataset loader
│   ├── indian_women_names_complete_1500.csv
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic Settings (all env vars)
│   │   ├── database.py         # SQLAlchemy engine, session, init_db
│   │   ├── security.py         # JWT, password hashing, OTP logic
│   │   ├── auth_deps.py        # Dependency providers (current user, admin, premium)
│   │   ├── exceptions.py       # Custom HTTP exceptions
│   │   ├── utils.py            # Age calculator
│   │   ├── uploads.py          # File upload validation + saving
│   │   ├── razorpay.py         # Razorpay payment integration
│   │   ├── mail.py             # SMTP email sender
│   │   └── geo.py              # Haversine distance calculator
│   ├── models/
│   │   └── __init__.py         # 15 SQLAlchemy ORM models
│   ├── schemas/
│   │   └── __init__.py         # 66 Pydantic models (requests/responses)
│   ├── services/
│   │   └── __init__.py         # Empty
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── rate_limit.py       # IP-based rate-limiting middleware
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py             # Auth endpoints (OTP, login, register, refresh)
│   │   ├── profile.py          # User profile CRUD, photos, languages
│   │   ├── discovery.py        # Discovery feed, swipes, swipe stats
│   │   ├── matches.py          # Matches list, messages, women-first check
│   │   ├── notifications.py    # Notification queries, read/unread, push tokens
│   │   ├── reports.py          # Report, block, unblock users
│   │   ├── family.py           # Family share create/revoke/view
│   │   ├── verification.py     # Phone + photo verification
│   │   ├── preferences.py      # User discovery preferences
│   │   ├── subscriptions.py    # Plans, order, verify, webhook, cancel
│   │   └── admin.py            # Full admin panel API
│   ├── websocket/
│   │   ├── __init__.py
│   │   └── handler.py          # WebSocket connection handler
│   └── static/
│       ├── admin/index.html    # Admin dashboard SPA
│       ├── checkout/index.html # Premium checkout page
│       ├── landing/index.html  # Public landing page
│       └── login/index.html    # Login/register page
└── tests/
    ├── __init__.py
    ├── conftest.py             # Fixtures (mock_db, sample_user)
    ├── test_api.py             # Endpoint smoke tests
    ├── test_exceptions.py      # Custom exception tests
    ├── test_geo.py             # Haversine distance tests
    ├── test_security.py        # JWT, password, OTP tests
    └── test_utils.py           # Age calculator tests
```

### Folder responsibilities

| Folder | Purpose | Dependencies |
|--------|---------|-------------|
| `src/core/` | Configuration, database engine, security primitives, authentication dependencies, custom exceptions, file uploads, payment/email/geo utilities | `core/config.py` |
| `src/models/` | SQLAlchemy ORM models (15 tables) | `core/database.py` |
| `src/schemas/` | Pydantic request/response models (66 models) | — |
| `src/services/` | Empty — intended for business logic layer | — |
| `src/middleware/` | Custom Starlette middleware (rate limiting) | — |
| `src/routers/` | FastAPI APIRouter endpoints (11 routers) | `core/`, `models/`, `schemas/` |
| `src/websocket/` | WebSocket endpoint and connection manager | `core/security.py` |
| `src/static/` | Static HTML/JS pages served directly by FastAPI | — |
| `src/` root | `main.py` (app entry), `seed.py`, `generate_dummy_data.py` | `core/`, `models/` |
| `tests/` | Pytest test suite | `src/` |
| `migrations/` | Raw SQL migration scripts | — |

---

## 3. Application Startup

**Entry point:** `src/main.py:app`

### App initialization sequence (`src/main.py:32-40`)

```python
app = FastAPI(
    title=settings.APP_NAME,   # "Brownies Dating App"
    version="1.0.0",
    lifespan=lifespan,
)
```

### Lifespan events (`src/main.py:20-23`)

1. **Startup:** `init_db()` creates all tables via `Base.metadata.create_all`, then runs `migrate_missing_columns()` which dynamically adds missing columns to existing tables. This serves as auto-migration on startup.
2. **Startup:** `load_runtime_settings()` reads `app_settings` table and applies values to the in-memory `settings` object (max_photos_per_user, max_photo_size_mb, family_share_expire_days).
3. **Shutdown:** No explicit shutdown logic — the `yield` is empty.

### Middleware registration order (`src/main.py:42-49`)

1. `CORSMiddleware` — permissive (`allow_origins` from settings, all methods/headers, credentials=True)
2. `RateLimitMiddleware` — 100 requests per 60 seconds per IP

### Router registration (`src/main.py:51-62`)

All 11 routers are registered on the main app. Router prefixes are self-contained (each uses `settings.API_V1_PREFIX`). The WebSocket router gets the same prefix.

### Static file mounting (`src/main.py:65-79`)

- `/api/v1/uploads` → `data/uploads/` directory (photos and verification subdirs)
- `/login` → `static/login/`
- `/checkout` → `static/checkout/`
- `/admin` → `static/admin/`
- `/` → `static/landing/index.html` (landing page, conditional on file existence)

### Seed script (`src/seed.py`)

The Docker `entrypoint.sh` runs `python seed.py` before starting uvicorn. This creates:
- Default subscription plans (Free, Premium Monthly 499 INR, Premium Yearly 2999 INR)
- Default admin account (phone: 0000000000, password: admin123)
- Default user preferences for admin

---

## 4. Request Flow

```
Client
  │
  ▼
FastAPI App (main.py)
  │
  ├─ CORS Middleware ──── (adds CORS headers)
  ├─ RateLimit Middleware ─ (IP-based, 100 req/60s, exempts /ws and /uploads)
  │
  ▼
Router (APIRouter) ──── (matches by prefix)
  │
  ▼
Dependencies (Depends)
  ├─ get_db() ────────── (async session, commits on success, rollback on error)
  ├─ get_current_user() ─ (validates Bearer JWT, loads User, updates last_active)
  ├─ get_current_admin() ─ (checks phone in ADMIN_PHONES)
  ├─ get_premium_user() ─ (checks is_premium flag)
  │
  ▼
Endpoint Handler ─────── (business logic inline)
  │
  ▼
SQLAlchemy AsyncSession ── (query/insert/update/delete on models)
  │
  ▼
PostgreSQL 16 ─────────── (via asyncpg driver)
  │
  ▼
Response (Pydantic model serialized to JSON)
```

### Key implementation details

- **Session management:** `get_db()` (`src/core/database.py:32-36`) yields a session that commits on normal exit and rolls back on exception.
- **Auth flow:** `get_current_user()` (`src/core/auth_deps.py:23-41`) extracts the `Bearer` token, decodes it, validates the `type: "access"` claim, loads the user, updates `last_active`, and checks subscription expiry.
- **No service layer:** All business logic is inline within router endpoint functions.
- **No repository layer:** Database queries use SQLAlchemy `select()` directly in router handlers.

---

## 5. API Layer

### Router inventory

| Router | Prefix | Tags | File | Lines |
|--------|--------|------|------|-------|
| auth | `/api/v1/auth` | `["auth"]` | `routers/auth.py` | 181 |
| profile | `/api/v1/profile` | `["profile"]` | `routers/profile.py` | 221 |
| discovery | `/api/v1/discovery` | `["discovery"]` | `routers/discovery.py` | 300 |
| matches | `/api/v1/matches` | `["matches"]` | `routers/matches.py` | 274 |
| notifications | `/api/v1/notifications` | `["notifications"]` | `routers/notifications.py` | 80 |
| reports | `/api/v1` | `["reports"]` | `routers/reports.py` | 135 |
| family | `/api/v1` | `["family-share"]` | `routers/family.py` | 106 |
| verification | `/api/v1/verification` | `["verification"]` | `routers/verification.py` | 45 |
| preferences | `/api/v1/preferences` | `["preferences"]` | `routers/preferences.py` | 60 |
| subscriptions | `/api/v1/subscriptions` | `["subscriptions"]` | `routers/subscriptions.py` | 306 |
| admin | `/api/v1/admin` | `["admin"]` | `routers/admin.py` | 1,352 |
| ws | `/ws` | — | `websocket/handler.py` | 68 |
| app-level | `/`, `/api/subscribe`, `/api/v1/health` | — | `main.py` | — |

### Auth router endpoints (`src/routers/auth.py`)

| Method | Path | Purpose | Auth | Request | Response |
|--------|------|---------|------|---------|----------|
| POST | `/auth/send-otp` | Send OTP to phone | None | `SendOtpRequest` | `{success, retry_after_seconds, expires_in_seconds, otp?}` |
| POST | `/auth/verify-otp` | Verify OTP, return tokens | None | `VerifyOtpRequest` | `{access_token, refresh_token, token_type, is_new_user, profile_complete}` |
| POST | `/auth/set-password` | Set password for current user | JWT | `SetPasswordRequest` | `{success, message}` |
| POST | `/auth/login` | Login with phone/email + password | None | `LoginRequest` | `TokenResponse` |
| POST | `/auth/register` | Register with email + password | None | `RegisterRequest` | `{access_token, refresh_token, token_type, is_new_user, profile_complete}` |
| POST | `/auth/refresh` | Refresh access token | None | `RefreshTokenRequest` | `TokenResponse` |
| POST | `/auth/logout` | Logout (no-op) | None | — | `SuccessResponse` |
| DELETE | `/auth/account` | Delete own account | JWT | — | `SuccessResponse` |

### Profile router endpoints (`src/routers/profile.py`)

| Method | Path | Purpose | Auth | Request/Response |
|--------|------|---------|------|-----------------|
| GET | `/profile/me` | Get own profile | JWT | `UserProfileOut` |
| POST | `/profile/setup` | Complete profile setup | JWT | `SetupProfileRequest` → `UserProfileOut` |
| PATCH | `/profile/me` | Update profile fields | JWT | `UpdateProfileRequest` → `UserProfileOut` |
| POST | `/profile/photos` | Upload profile photo | JWT | `UploadFile` → `UserPhotoOut` |
| DELETE | `/profile/photos/{id}` | Delete photo | JWT | `SuccessResponse` |
| PUT | `/profile/photos/reorder` | Reorder photos | JWT | `ReorderPhotosRequest` → `SuccessResponse` |
| PUT | `/profile/languages` | Update languages | JWT | `UpdateLanguagesRequest` → `SuccessResponse` |
| GET | `/profile/{user_id}` | View another user's profile | JWT | `UserProfileOut` |

### Discovery router endpoints (`src/routers/discovery.py`)

| Method | Path | Purpose | Auth | Request/Response |
|--------|------|---------|------|-----------------|
| GET | `/discovery` | Get discovery feed | JWT | `list[DiscoveryProfileOut]` |
| POST | `/discovery/swipes` | Swipe on a user | JWT | `SwipeRequest` → `{success, direction, matched?, match_id?}` |
| POST | `/discovery/swipes/undo` | Undo last swipe | Premium JWT | `SuccessResponse` |
| GET | `/discovery/swipes/stats` | Get remaining likes/super-likes | JWT | `SwipeStatsOut` |

### Matches router endpoints (`src/routers/matches.py`)

| Method | Path | Purpose | Auth | Request/Response |
|--------|------|---------|------|-----------------|
| GET | `/matches` | List active matches | JWT | `list[MatchOut]` |
| GET | `/matches/{id}` | Get match detail | Premium JWT | `MatchOut` |
| DELETE | `/matches/{id}` | Unmatch | JWT | `SuccessResponse` |
| GET | `/matches/{id}/messages` | Get messages | Premium JWT | `list[MessageListItem]` |
| POST | `/matches/{id}/messages` | Send message | Premium JWT | `SendMessageRequest` → `MessageOut` |
| GET | `/matches/{id}/women-first-status` | Check women-first gate | Premium JWT | `WomenFirstStatus` |
| PUT | `/matches/{id}/messages/read` | Mark messages read | Premium JWT | `SuccessResponse` |

### Notifications router endpoints (`src/routers/notifications.py`)

| Method | Path | Purpose | Auth | Request/Response |
|--------|------|---------|------|-----------------|
| GET | `/notifications` | List notifications (paginated) | JWT | `list[NotificationOut]` |
| GET | `/notifications/unread-count` | Get unread count | JWT | `{unread_count}` |
| PUT | `/notifications/{id}/read` | Mark one as read | JWT | `SuccessResponse` |
| PUT | `/notifications/read-all` | Mark all as read | JWT | `SuccessResponse` |
| POST | `/notifications/push-token` | Register FCM push token | JWT | `SuccessResponse` |

### Reports router endpoints (`src/routers/reports.py`)

| Method | Path | Purpose | Auth | Request/Response |
|--------|------|---------|------|-----------------|
| POST | `/reports` | Report a user | JWT | `ReportRequest` → `SuccessResponse` |
| POST | `/blocks` | Block a user | JWT | `ReportRequest` → `SuccessResponse` |
| DELETE | `/blocks/{target_id}` | Unblock a user | JWT | `SuccessResponse` |
| GET | `/blocks` | List blocked users | JWT | `list[BlockedUserOut]` |

### Family share router endpoints (`src/routers/family.py`)

| Method | Path | Purpose | Auth | Request/Response |
|--------|------|---------|------|-----------------|
| POST | `/family-share/{match_id}` | Create share link | JWT | `FamilyShareRequest` → `FamilyShareOut` |
| GET | `/shared/{token}` | View shared profile | None | `SharedProfileOut` |
| DELETE | `/family-share/{share_id}` | Revoke share | JWT | `SuccessResponse` |

### Verification router endpoints (`src/routers/verification.py`)

| Method | Path | Purpose | Auth | Request/Response |
|--------|------|---------|------|-----------------|
| GET | `/verification/status` | Get verification status | JWT | `VerificationStatusOut` |
| POST | `/verification/phone/send-otp` | Send verification OTP | JWT | `{success, expires_in_seconds, otp}` |
| POST | `/verification/phone/verify` | Verify phone via OTP | JWT | `SuccessResponse` |
| POST | `/verification/photo` | Submit photo verification | JWT | `SuccessResponse` |

### Preferences router endpoints (`src/routers/preferences.py`)

| Method | Path | Purpose | Auth | Request/Response |
|--------|------|---------|------|-----------------|
| GET | `/preferences` | Get discovery preferences | JWT | `PreferencesOut` |
| PUT | `/preferences` | Update preferences | JWT | `UpdatePreferencesRequest` → `PreferencesOut` |
| PUT | `/preferences/notification-settings` | Update notification settings | JWT | `UpdateNotificationSettingsRequest` → `SuccessResponse` |

### Subscriptions router endpoints (`src/routers/subscriptions.py`)

| Method | Path | Purpose | Auth | Request/Response |
|--------|------|---------|------|-----------------|
| GET | `/subscriptions/plans` | List active plans | None | `{plans: [...]}` |
| GET | `/subscriptions/me` | Get my subscription | JWT | `SubscriptionOut` |
| POST | `/subscriptions/order` | Create Razorpay order | JWT | `SubscriptionOrderOut` |
| POST | `/subscriptions/verify` | Verify payment & activate | JWT | `SuccessResponse` |
| POST | `/subscriptions/webhook` | Razorpay webhook handler | None (signature) | `{status}` |
| POST | `/subscriptions/cancel` | Cancel subscription | JWT | `SuccessResponse` |
| POST | `/subscriptions/web-order` | Web checkout order (phone+OTP) | None | `{order_id, amount, currency, key_id}` |
| POST | `/subscriptions/web-verify` | Web checkout verify (no JWT) | None | `SuccessResponse` |

### Admin router endpoints (`src/routers/admin.py`)

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/admin/dashboard` | Dashboard stats | Admin JWT |
| GET | `/admin/users` | Paginated user list | Admin JWT |
| GET | `/admin/users/export` | Export users (JSON/CSV) | Admin JWT |
| POST | `/admin/users/import` | Import users from JSON | Admin JWT |
| GET | `/admin/users/{id}` | User detail | Admin JWT |
| GET | `/admin/users/{id}/stats` | User activity stats | Admin JWT |
| GET | `/admin/users/{id}/swipes` | User swipe history | Admin JWT |
| GET | `/admin/users/{id}/matches` | User match history | Admin JWT |
| GET | `/admin/users/{id}/messages` | User message history | Admin JWT |
| PATCH | `/admin/users/{id}` | Quick update user (active/premium/verified) | Admin JWT |
| PUT | `/admin/users/{id}` | Full edit user | Admin JWT |
| POST | `/admin/users/{id}/reset-password` | Reset user password | Admin JWT |
| POST | `/admin/users/{id}/assign-plan` | Assign plan to user | Admin JWT |
| POST | `/admin/users/{id}/remove-plan` | Remove plan from user | Admin JWT |
| POST | `/admin/users` | Create user | Admin JWT |
| DELETE | `/admin/users/{id}` | Delete user | Admin JWT |
| GET | `/admin/photos` | List all photos | Admin JWT |
| DELETE | `/admin/photos/{id}` | Delete photo | Admin JWT |
| GET | `/admin/subscriptions` | List all subscriptions | Admin JWT |
| GET | `/admin/chats` | List all chat conversations | Admin JWT |
| GET | `/admin/chats/{match_id}/messages` | View chat messages | Admin JWT |
| GET | `/admin/matches` | List all matches | Admin JWT |
| POST | `/admin/matches` | Create match | Admin JWT |
| PATCH | `/admin/matches/{id}` | Update match active status | Admin JWT |
| DELETE | `/admin/matches/{id}` | Delete match | Admin JWT |
| GET | `/admin/plans` | List plans | Admin JWT |
| POST | `/admin/plans` | Create plan | Admin JWT |
| PUT | `/admin/plans/{id}` | Update plan | Admin JWT |
| DELETE | `/admin/plans/{id}` | Delete plan | Admin JWT |
| GET | `/admin/limits` | Get app limits | Admin JWT |
| PUT | `/admin/limits` | Update app limits | Admin JWT |
| GET | `/admin/reports` | List reports (paginated) | Admin JWT |
| POST | `/admin/reports/{id}/action` | Handle report (ban/dismiss) | Admin JWT |
| GET | `/admin/waitlist` | List waitlist subscribers | Admin JWT |
| GET | `/admin/stats/gender` | Gender distribution | Admin JWT |
| GET | `/admin/stats/cities` | Top 20 cities | Admin JWT |
| POST | `/admin/dummy-data/generate` | Generate dummy data (SSE) | Admin JWT |
| POST | `/admin/dummy-data/reset` | Clear dummy data | Admin JWT |

### App-level endpoints (`src/main.py`)

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/api/v1/health` | Health check | None |
| POST | `/api/subscribe` | Waitlist signup | None |
| GET | `/` | Landing page (HTML) | None |

---

## 6. Dependency Injection

### Dependency providers (`src/core/auth_deps.py`)

```
get_db()
  └── yields AsyncSession, commits/rollback automatically

get_current_user(authorization: Header, db: Depends(get_db))
  ├── validates Bearer <token>
  ├── decodes JWT, checks type=="access"
  ├── loads User from DB
  ├── updates user.last_active
  ├── checks subscription expiry → removes premium if expired
  └── returns User

get_current_admin(user: Depends(get_current_user))
  ├── checks user.phone_number in ADMIN_PHONES
  └── returns User (or 403)

get_premium_user(user: Depends(get_current_user))
  ├── checks user.is_premium
  └── returns User (or 402)
```

### Dependency graph

```
routes requiring auth:
  get_current_user ────────► get_db()
      │
      ├─► get_current_admin ──► get_current_user
      └─► get_premium_user ───► get_current_user

routes not requiring auth:
  get_db() (used in /auth endpoints for OTP, login, register)
```

### Singleton services

There are no singleton services in the application. The following are module-level singletons (not dependency-injected):

- `settings` (`core/config.py:73`) — global Settings instance
- `engine` / `async_session` (`core/database.py:7-13`) — global SQLAlchemy engine/sessionmaker
- `active_connections` (`websocket/handler.py:6`) — global dict of WebSocket connections
- `otp_store` / `otp_attempts` (`core/security.py:15-16`) — global in-memory OTP stores (legacy sync version)

---

## 7. Business Logic

### Service layer status

The `src/services/` directory contains only an empty `__init__.py`. **There is no service layer.** All business logic is embedded directly within router endpoint functions.

### Business logic locations by domain

| Domain | Location | Key logic |
|--------|----------|-----------|
| Authentication | `routers/auth.py` | OTP generation/verification, user creation on first login, JWT issuance, account deletion |
| Profile | `routers/profile.py` | Profile setup/update, photo management (max 6, primary flag), language management |
| Discovery | `routers/discovery.py` | Feed query with preferences filtering, swipe creation with daily limits, match detection, notification creation, undo (premium) |
| Matching | `routers/discovery.py:226-255` | Mutual-like detection, match creation, dual notification |
| Messaging | `routers/matches.py` | Message send/receive, women-first gate (male cannot send first message in male-female match), message read status |
| Subscriptions | `routers/subscriptions.py` | Plan listing, Razorpay order creation, payment verification, webhook processing, subscription activation/cancellation, stacked subscriptions |
| Family Sharing | `routers/family.py` | Token generation, time-limited access, profile view by token |
| Verification | `routers/verification.py` | Phone OTP verification, photo verification submission |
| Blocking | `routers/reports.py` | Block with auto-unmatch, unblock, report with dedup |
| Admin | `routers/admin.py` | User CRUD, match CRUD, plan CRUD, report handling, import/export, limits management, stats, dummy data generation |

### Business rules implemented

1. **OTP rate limiting:** 3 requests per 10-minute window per phone number (`core/security.py:67-85`)
2. **Daily swipe limits:** Free users get 50 likes + 1 super like/day; premium plans override these (`core/config.py:40-41`, `routers/discovery.py:28-47`)
3. **Women-first messaging:** In male-female matches with no prior messages, the male user cannot send the first message (`routers/matches.py:237-242`)
4. **Subscription stacking:** If a user has an active subscription and buys another, the new one starts after the current one ends (`routers/subscriptions.py:27-32`)
5. **Block auto-unmatch:** Blocking a user automatically deactivates any mutual match (`routers/reports.py:80-87`)
6. **Profile completion gate:** Discovery only shows users with `profile_complete = True` (`routers/discovery.py:113`)
7. **Photos limit:** Max 6 photos per user, configurable via `AppSetting` (`core/config.py:39`, `routers/admin.py:1158-1207`)

---

## 8. Data Layer

### Database technology

- **Database:** PostgreSQL 16 (Alpine variant in Docker)
- **Driver:** `asyncpg` (async PostgreSQL driver)
- **ORM:** SQLAlchemy 2.0 with async support
- **Connection string:** `postgresql+asyncpg://brownies:brownies@db:5432/brownies`

### Session management (`src/core/database.py:32-36`)

```python
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- Sessions auto-commit on success and auto-rollback on exception.
- `expire_on_commit=False` to allow detached object access.
- `pool_pre_ping=True` for connection health checks.
- Pool size: 20, max overflow: 10, recycle: 3600s (configurable).

### Transaction management

- Each request operates within a single session/transaction.
- No explicit nested transactions or savepoints.
- No unit-of-work pattern.

### Repository pattern

**Not implemented.** All database queries are inline SQLAlchemy `select()`/`insert()` calls within router handlers.

### Connection lifecycle

1. `async_session()` creates a new session from the pool
2. Session is yielded to the endpoint
3. On return: session commits
4. On exception: session rolls back
5. Session is closed (returned to pool)

### Migrations

- **Auto-migration:** `init_db()` (`src/core/database.py:38-62`) automatically creates tables and adds missing columns on startup.
- **Manual SQL:** `migrations/001_add_performance_indexes.sql` contains production indexes that must be run manually.
- No migration framework (Alembic) is used.

---

## 9. Models

### Database models (SQLAlchemy ORM) — `src/models/__init__.py`

| Model | Table | Primary Key | Key Relationships | Indexes |
|-------|-------|-------------|-------------------|---------|
| `User` | `users` | `id` (auto) | photos, languages, preferences, swipes_made, swipes_received | phone_number, city |
| `UserPhoto` | `user_photos` | `id` (auto) | FK → users.id (CASCADE) | user_id |
| `UserLanguage` | `user_languages` | `id` (auto) | FK → users.id (CASCADE) | — |
| `UserPreferences` | `user_preferences` | `id` (auto) | FK → users.id (CASCADE, unique) | user_id (unique) |
| `Swipe` | `swipes` | `id` (auto) | FK → users.id (swiper), FK → users.id (swiped) | swiper_id, swiped_id, unique(swiper_id, swiped_id) |
| `Match` | `matches` | `id` (auto) | FK → users (user1, user2, unmatched_by) | unique(user1_id, user2_id), check(user1_id < user2_id) |
| `Message` | `messages` | `id` (auto) | FK → matches.id (CASCADE), FK → users.id | match_id |
| `BlockReport` | `blocks_reports` | `id` (auto) | FK → users (reporter, reported) | unique(reporter_id, reported_id, type) |
| `Notification` | `notifications` | `id` (auto) | FK → users.id (CASCADE) | user_id |
| `FamilyShare` | `family_shares` | `id` (auto) | FK → users (user, profile_user) | access_token (unique) |
| `Subscription` | `subscriptions` | `id` (auto) | FK → users.id (CASCADE), FK → plans.id (SET NULL) | user_id, payment_id |
| `Plan` | `plans` | `id` (auto) | — | — |
| `AppSetting` | `app_settings` | `key` (PK) | — | — |
| `WaitlistSubscriber` | `waitlist_subscribers` | `id` (auto) | — | email (unique) |
| `OtpRecord` | `otp_records` | `id` (auto) | — | phone |

### Pydantic models — `src/schemas/__init__.py`

66 Pydantic models organized into:

- **Auth:** 8 models (OTP, login, register, token)
- **Profile:** 8 models (setup, update, photo, language, profile out, summary)
- **Discovery:** 1 model (profile card with distance)
- **Swipes:** 2 models (swipe request, stats)
- **Matches:** 1 model (match list item)
- **Messages:** 4 models (message, list item, send request, women-first status)
- **Family Share:** 3 models
- **Verification:** 1 model
- **Preferences:** 3 models
- **Notifications:** 1 model
- **Reports & Blocks:** 2 models
- **Subscriptions:** 3 models
- **Admin:** 20+ models (dashboard, users, plans, reports, photos, chats, stats, pagination)
- **Common:** 1 model (`SuccessResponse`)

### Relationships

- **User → UserPhoto:** one-to-many (cascade delete)
- **User → UserLanguage:** one-to-many (cascade delete)
- **User → UserPreferences:** one-to-one (cascade delete, unique constraint)
- **User → Swipe (made):** one-to-many (cascade delete)
- **User → Swipe (received):** one-to-many (cascade delete)
- **Match → Message:** one-to-many (cascade delete)
- **Match has two User FKs** (user1_id, user2_id) with enforced ordering: user1_id < user2_id

### Inheritance

No model inheritance is used. All models extend `Base` directly.

### Validation

- Pydantic models provide field-level validation (min_length, max_length, Field constraints).
- No custom Pydantic validators or `@field_validator` decorators are defined.
- Database-level constraints: unique, check, foreign key with cascade.

---

## 10. Authentication & Authorization

### Authentication method

**JWT-based with phone OTP as the primary gateway.**

- Users authenticate by phone number + OTP (`/auth/send-otp` then `/auth/verify-otp`).
- On first login, a User record is auto-created with blank profile fields.
- Email/password registration and login are also supported as secondary paths.
- The `authorization: Bearer <token>` header is required for all protected endpoints.

### Token lifecycle (`src/core/security.py`)

| Token | Type | Default TTL | Config |
|-------|------|-------------|--------|
| Access Token | `"access"` JWT | 60 minutes | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh Token | `"refresh"` JWT | 30 days | `REFRESH_TOKEN_EXPIRE_DAYS` |

- Algorithm: `HS256` (symmetric, configurable via `JWT_ALGORITHM`).
- Token payload: `{"sub": user_id, "exp": timestamp, "type": "access"|"refresh"}`.
- Refresh endpoint issues both a new access token and a new refresh token (rotation).

### Password hashing

- Algorithm: `bcrypt` via `passlib` (`src/core/security.py:11`).
- Constraint: `bcrypt<4.1` pinned in `requirements.txt`.

### OTP (`src/core/security.py`)

- 6-digit numeric code.
- TTL: 300 seconds (configurable).
- Rate limit: 3 per 10 minutes per phone.
- Stored in database (`otp_records` table) for async API routes.
- Legacy in-memory store (`otp_store` dict) still exists for sync compatibility.
- Bypass: if `OTP_BYPASS` env var is set, any value matches.

### Authorization levels

| Level | Dependency | How granted |
|-------|-----------|-------------|
| Public | No dependency | Any request |
| Authenticated | `get_current_user` | Valid Bearer access token |
| Premium | `get_premium_user` | `User.is_premium == True` (402 if not) |
| Admin | `get_current_admin` | `User.phone_number` in `ADMIN_PHONES` list (403 if not) |

### Security dependencies (`src/core/auth_deps.py`)

- `get_current_user` validates Bearer token, loads user, updates `last_active`, checks subscription expiry.
- `get_current_admin` calls `get_current_user` then checks admin phone list.
- `get_premium_user` calls `get_current_user` then checks premium flag.

### Admin identification

Admins are identified by phone number whitelist in `ADMIN_PHONES` (default: `["0000000000"]`). There is no `is_admin` flag on the User model.

---

## 11. Middleware

### Rate Limit Middleware (`src/middleware/rate_limit.py`)

| Property | Value |
|----------|-------|
| Class | `RateLimitMiddleware(BaseHTTPMiddleware)` |
| Default limit | 100 requests per 60 seconds |
| Scope | Per client IP |
| Storage | In-memory `defaultdict[list[datetime]]` |
| Exemptions | `/ws` path, `/api/v1/uploads` path |
| Response | HTTP 429 with `Retry-After` header |

### CORS Middleware (configured in `src/main.py:42-47`)

| Setting | Value |
|---------|-------|
| Origins | Configurable via `CORS_ORIGINS`, defaults to localhost:3000, 5173, 8081 + datebrownies.com |
| Methods | All (`*`) |
| Headers | All (`*`) |
| Credentials | True |

### Execution order

1. CORS middleware (outermost)
2. Rate Limit middleware (inner)

No other middleware (compression, logging, trusted host, etc.) is configured.

---

## 12. Configuration

### Configuration source (`src/core/config.py`)

- **Class:** `Settings(BaseSettings)` from `pydantic-settings`
- **File:** `.env` (auto-loaded via `model_config`)
- **Instance:** Global `settings` singleton at module level

### Environment variables

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `APP_NAME` | `"Brownies Dating App"` | No | App title |
| `API_V1_PREFIX` | `"/api/v1"` | No | API prefix |
| `DEBUG` | `false` | No | Enable debug (shows OTP in response) |
| `DATABASE_URL` | `postgresql+asyncpg://brownies:brownies@localhost:5432/brownies` | Yes | Database connection |
| `DATABASE_ECHO` | `false` | No | SQL logging |
| `DB_POOL_SIZE` | `20` | No | Connection pool size |
| `DB_MAX_OVERFLOW` | `10` | No | Max pool overflow |
| `DB_POOL_RECYCLE` | `3600` | No | Pool recycle seconds |
| `JWT_SECRET` | `"brownies-dev-secret-change-in-production"` | **Yes** | JWT signing key |
| `JWT_ALGORITHM` | `"HS256"` | No | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | No | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | No | Refresh token TTL |
| `OTP_BYPASS` | `""` | No | If set, any OTP matches this value |
| `OTP_LENGTH` | `6` | No | OTP digit count |
| `OTP_EXPIRE_SECONDS` | `300` | No | OTP TTL |
| `OTP_RATE_LIMIT` | `3` | No | Max OTP requests per window |
| `OTP_RATE_WINDOW_MINUTES` | `10` | No | OTP rate limit window |
| `TWILIO_ACCOUNT_SID` | `""` | No | Twilio SID (not used in code — dead config) |
| `TWILIO_AUTH_TOKEN` | `""` | No | Twilio auth token (not used) |
| `TWILIO_PHONE` | `""` | No | Twilio phone number (not used) |
| `UPLOAD_DIR` | `Path("data/uploads")` | No | Upload storage directory |
| `MAX_PHOTO_SIZE_MB` | `10` | No | Max photo size (MB) |
| `MAX_PHOTOS_PER_USER` | `6` | No | Max photos per user |
| `DAILY_LIKES_FREE` | `50` | No | Free daily likes |
| `DAILY_SUPER_LIKES_FREE` | `1` | No | Free daily super likes |
| `FAMILY_SHARE_EXPIRE_DAYS` | `7` | No | Share link expiry |
| `FAMILY_SHARE_TOKEN_LENGTH` | `32` | No | Share token bytes |
| `SMTP_HOST` | `""` | No | SMTP server |
| `SMTP_PORT` | `587` | No | SMTP port |
| `SMTP_USER` | `""` | No | SMTP username |
| `SMTP_PASSWORD` | `""` | No | SMTP password |
| `SMTP_FROM_NAME` | `"Brownies"` | No | Sender name |
| `NOTIFY_EMAIL` | `""` | No | Notification recipient |
| `RAZORPAY_KEY_ID` | `""` | No | Razorpay API key |
| `RAZORPAY_KEY_SECRET` | `""` | No | Razorpay API secret |
| `RAZORPAY_WEBHOOK_SECRET` | `""` | No | Razorpay webhook secret |
| `ADMIN_PHONES` | `["0000000000"]` | No | Admin phone whitelist |
| `CORS_ORIGINS` | `""` | No | Comma-separated CORS origins |

### Runtime settings override

The `app_settings` database table can override `MAX_PHOTOS_PER_USER`, `MAX_PHOTO_SIZE_MB`, and `FAMILY_SHARE_EXPIRE_DAYS` at runtime via the admin API. These are loaded on startup (`load_runtime_settings()` in `main.py:9-18`) and can be updated via `PUT /admin/limits` without restart.

### Secrets management

- No secret manager / vault integration.
- Secrets are provided via environment variables.
- Dev defaults are hardcoded and insecure (JWT secret, DB credentials).

---

## 13. External Integrations

### Razorpay (`src/core/razorpay.py`)

| Aspect | Detail |
|--------|--------|
| Purpose | Payment processing for premium subscriptions |
| SDK | `razorpay` Python package |
| Auth | Key ID + Key Secret |
| Methods | `create_order`, `verify_signature`, `verify_webhook_signature`, `fetch_payment` |
| Used in | `routers/subscriptions.py` |
| Dev mode | When no key configured, returns fake order IDs and skips verification |

### Twilio (configured but not used)

The `requirements.txt` lists `twilio` as a dependency and the settings define `TWILIO_*` variables, but **no Twilio code is present in the application**. OTPs are currently returned in API responses (visible in dev mode) rather than sent via SMS.

### SMTP Email (`src/core/mail.py`)

| Aspect | Detail |
|--------|--------|
| Purpose | Email notifications for waitlist signups |
| Method | `smtplib.SMTP` with STARTTLS |
| Used in | `main.py` (`/api/subscribe`) |
| Dev mode | Prints to stdout when SMTP not configured |

### Databases

- PostgreSQL 16 via `asyncpg` driver — primary data store.
- No Redis, no Elasticsearch, no message queue.

---

## 14. Background Processing

### Background tasks

**Not implemented.** There is no use of FastAPI `BackgroundTasks` or any background worker framework. No Celery, RQ, or Redis queues are configured. No scheduled/cron jobs exist.

### Async operations

All database operations are async (`asyncpg` + `AsyncSession`). Blocking I/O (file uploads via `aiofiles`, SMTP in sync `smtplib`) is not explicitly offloaded to thread pools.

---

## 15. Error Handling

### Custom exceptions (`src/core/exceptions.py`)

| Exception | Status | Code | Notes |
|-----------|--------|------|-------|
| `AppException` | configurable | `"error"` | Base class, extends `HTTPException` |
| `AuthException` | 401 | `"auth_error"` | Authentication failures |
| `ForbiddenException` | 403 | `"forbidden"` | Access denied |
| `NotFoundException` | 404 | `"not_found"` | Resource not found |
| `ConflictException` | 409 | `"conflict"` | Duplicate resource |
| `ValidationException` | 422 | `"validation_error"` | Invalid input |
| `RateLimitException` | 429 | `"rate_limit"` | Includes `Retry-After` header |
| `PaymentRequiredException` | 402 | `"payment_required"` | Premium feature gate |
| `VerificationRequiredException` | 403 | `"verification_required"` | Not yet verified |

### Error handling patterns

- All custom exceptions are subclasses of Starlette's `HTTPException` so FastAPI handles them natively.
- **No global exception handlers** are registered. Unhandled exceptions will produce 500 errors with default FastAPI tracebacks.
- **No custom validation error handler** — Pydantic validation errors use FastAPI defaults (422 with detail array).

---

## 16. Logging & Observability

### Logging configuration

**No logging configuration exists in the application code.** There is no `logging.basicConfig()`, no structured logging, and no log levels defined. The only output is:

- `print()` statements in `seed.py` (admin creation logs)
- `print()` in `database.py` (column migration logs)
- `print()` in `mail.py` (SMTP status)
- SQL echo via `DATABASE_ECHO` setting (off by default)

### Health endpoint

- `GET /api/v1/health` — returns `{"status": "ok", "app": settings.APP_NAME}`
- Docker healthcheck uses this endpoint.

### Metrics / Tracing / APM

**Not implemented.** No Prometheus, OpenTelemetry, Sentry, or any observability tooling.

---

## 17. Database Schema Overview

### Tables

| Table | Primary purpose | Approx. columns |
|-------|----------------|-----------------|
| `users` | Core user profiles | 30 |
| `user_photos` | Profile photos (up to 6) | 5 |
| `user_languages` | Languages spoken | 3 |
| `user_preferences` | Discovery filters | 7 |
| `swipes` | Like/pass/super_like records | 5 |
| `matches` | Mutual likes | 6 |
| `messages` | Chat messages | 6 |
| `blocks_reports` | Blocks and reports | 5 |
| `notifications` | User notifications | 7 |
| `family_shares` | Profile share tokens | 7 |
| `subscriptions` | Payment subscriptions | 7 |
| `plans` | Subscription plan definitions | 16 |
| `app_settings` | Key-value runtime settings | 2 |
| `waitlist_subscribers` | Landing page signups | 4 |
| `otp_records` | OTP storage | 6 |

### Relationships

```
users (1) ──< user_photos (many)
users (1) ──< user_languages (many)
users (1) ─── user_preferences (1:1)
users (1) ──< swipes (as swiper)
users (1) ──< swipes (as swiped)
users (1) ─── matches (as user1 or user2)
matches (1) ──< messages (many)
users (1) ──< blocks_reports (as reporter)
users (1) ──< blocks_reports (as reported)
users (1) ──< notifications (many)
users (1) ──< family_shares (as creator, as profile owner)
users (1) ──< subscriptions (many)
plans (1) ──< subscriptions (many, nullable)
users (1) ──< otp_records (many, by phone)
```

### Major entities

- **User:** Central entity — everything relates back to users.
- **Swipe:** Records a moment of interaction between two users.
- **Match:** Created when two users mutually swipe right.
- **Message:** Chat messages within a match.
- **Subscription:** Links users to paid plans for premium features.

### Indexes (from `migrations/001_add_performance_indexes.sql`)

The recommended production indexes cover: users discovery feed, users gender, users intent, users city (active), swipes by swiper + date, swipes by swiper + swiped, messages by match + date, notifications by user + read/date, blocks/reports by reporter + type, subscriptions by user + active, OTP records by phone + expiry, family shares by token, matches by active + date.

---

## 18. Async Architecture

### Async endpoints

All router endpoints use `async def` and `await` for database operations. The application uses:

- `asyncpg` driver for PostgreSQL — fully async
- `AsyncSession` from SQLAlchemy — async ORM
- `aiofiles` for file uploads — async file I/O

### Sync operations (not offloaded)

- `smtplib.SMTP` in `core/mail.py` — synchronous, runs in the event loop thread
- `bcrypt` password hashing in `core/security.py` — CPU-bound, runs synchronously
- Razorpay SDK calls in `core/razorpay.py` — synchronous HTTP calls

**No `run_in_executor()` or thread pool offloading is implemented.** These synchronous operations could block the event loop under load.

### WebSocket (`src/websocket/handler.py`)

- Single endpoint: `ws://host/ws`
- Authentication via first message: `{"token": "jwt_token"}`
- Connection tracking: `active_connections: dict[int, WebSocket]`
- Message types: `ping`/`pong` (keepalive), `typing_start`/`typing_stop` (ack-only, no relay)
- The `notify_user()` utility function allows pushing events to connected users.

---

## 19. Security Review

### Security mechanisms present

| Mechanism | Implementation |
|-----------|---------------|
| JWT authentication | Access/refresh tokens, HS256, typed tokens, expiry |
| Password hashing | bcrypt via passlib |
| OTP | 6-digit, time-limited, rate-limited, single-use |
| Phone verification | Required for full profile access |
| Photo verification | Upload → admin review |
| Rate limiting | IP-based (100 req/60s) |
| CORS | Configurable origins, credentials |

### Potential risks

1. **Hardcoded default JWT secret** (`"brownies-dev-secret-change-in-production"`) — if not overridden in production, tokens are forgeable.
2. **OTP returned in API response** — In dev mode (`DEBUG=true`), the OTP is returned in the `send-otp` response body. This defeats the purpose of OTP.
3. **No SMS integration** — Twilio is configured but not used. OTPs are not actually sent to phones.
4. **No CSRF protection** — Form endpoints (login, checkout) have no CSRF tokens.
5. **No rate limiting on auth endpoints** — Auth endpoints bypass the general rate limit? (The rate limit middleware only exempts `/ws` and `/uploads`. Auth endpoints ARE rate-limited via the middleware, but OTP-specific rate limiting only applies to send-otp, not login/register.)
6. **No account lockout** — No brute-force protection on login beyond IP rate limiting.
7. **No request size limiting** — Photo uploads have size checks but general request body size is unbounded.
8. **File upload validation** — Extensions and MIME types checked client-side only (no server-side content inspection or virus scanning).
9. **In-memory rate limit storage** — Lost on restart, not suitable for multi-instance deployments.
10. **No audit logging** — No record of admin actions, sensitive operations.
11. **Session commit before response** — The `get_db` dependency commits the session before the response is sent. If the response serialization fails, the transaction is already committed.

### Missing protections

- No `X-Content-Type-Options`, `X-Frame-Options`, or `Strict-Transport-Security` headers.
- No request body size limits.
- No content security policy.
- No dependency scanning / SCA tooling evident.

---

## 20. Design Patterns

### Patterns actually used

| Pattern | Where | Notes |
|---------|-------|-------|
| **Dependency Injection** | FastAPI `Depends()` | Core pattern — auth deps, DB session, user loading |
| **Singleton** | `settings`, `engine`, `async_session` | Module-level globals |
| **Active Record (variation)** | SQLAlchemy ORM models | Models mix data and persistence (via session) |
| **Template/Callback** | `generate_dummy_data()` generator | Yields progress events for SSE streaming |
| **Middleware Chain** | CORS → Rate Limit | Starlette middleware pipeline |
| **Strategy (implicit)** | OTP verification (sync in-memory vs async DB-backed) | Two implementations, selected by calling context |
| **Decorator** | `@router.get/post/put/delete/patch/websocket` | FastAPI routing decorators |

### Patterns NOT used

- **Repository** — No repository layer exists. Queries are inline.
- **Service Layer** — The `services/` directory is empty.
- **Unit of Work** — No transaction boundaries beyond single-session-per-request.
- **Factory** — No factory functions for model/entity creation.
- **Builder** — No builder pattern.
- **Adapter** — No adapter pattern for external services.
- **Facade** — No facade classes.
- **Event Driven** — No events, no message bus.
- **CQRS** — No command/query separation.
- **Domain Events** — Not used.

---

## 21. Architectural Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        A[Mobile App]
        B[Web Browser]
        C[Admin Dashboard]
        D[Razorpay Webhook]
    end

    subgraph "FastAPI Application"
        subgraph "Middleware"
            M1[CORS Middleware]
            M2[Rate Limit Middleware]
        end

        subgraph "Routers"
            R1[Auth Router]
            R2[Profile Router]
            R3[Discovery Router]
            R4[Matches Router]
            R5[Messages Router]
            R6[Notifications Router]
            R7[Reports Router]
            R8[Family Router]
            R9[Verification Router]
            R10[Preferences Router]
            R11[Subscriptions Router]
            R12[Admin Router]
            R13[WebSocket Handler]
        end

        subgraph "Core Infrastructure"
            C1[Security / JWT / OTP]
            C2[Auth Dependencies]
            C3[File Uploads]
            C4[Razorpay Client]
            C5[Email Client]
            C6[Geo Calculator]
        end

        subgraph "Data Layer"
            D1[SQLAlchemy Async Engine]
            D2[ORM Models]
            D3[Session Manager]
        end

        subgraph "Static Assets"
            S1[Landing Page]
            S2[Login Page]
            S3[Checkout Page]
            S4[Admin Dashboard HTML]
        end
    end

    subgraph "External Services"
        E1[(PostgreSQL 16)]
        E2[Razorpay API]
        E3[SMTP Server]
        E4[(File System)]
    end

    A --> M1
    B --> M1
    C --> M1
    D --> M1

    M1 --> M2
    M2 --> R1 & R2 & R3 & R4 & R5 & R6 & R7 & R8 & R9 & R10 & R11 & R12 & R13 & S1 & S2 & S3 & S4

    R1 & R2 & R3 & R4 & R5 & R6 & R7 & R8 & R9 & R10 & R11 & R12 --> C2
    C2 --> C1
    R1 & R2 & R3 & R4 & R5 & R6 & R7 & R8 & R9 & R10 & R11 & R12 --> D3
    D3 --> D1
    D1 --> E1
    R11 --> C4 --> E2
    S1 --> C5 --> E3
    R2 & R9 --> C3 --> E4
    R3 --> C6

    style E1 fill:#336791,color:#fff
    style E2 fill:#3395FF,color:#fff
    style E3 fill:#D14836,color:#fff
```

---

## 22. Dependency Graph

### Module-level dependencies

```
main.py
  ├── core/config.py
  ├── core/database.py
  │     └── core/config.py
  ├── middleware/rate_limit.py
  ├── routers/auth.py
  │     ├── core/config.py
  │     ├── core/database.py
  │     ├── core/security.py
  │     ├── core/exceptions.py
  │     ├── core/auth_deps.py
  │     ├── models/__init__.py
  │     └── schemas/__init__.py
  ├── routers/profile.py
  │     ├── core/... (same pattern)
  │     ├── core/uploads.py
  │     └── core/utils.py
  ├── routers/discovery.py
  │     ├── core/geo.py
  │     └── core/utils.py
  ├── routers/matches.py
  ├── routers/notifications.py
  ├── routers/reports.py
  ├── routers/family.py
  ├── routers/verification.py
  ├── routers/preferences.py
  ├── routers/subscriptions.py
  │     └── core/razorpay.py
  ├── routers/admin.py
  │     └── generate_dummy_data.py
  ├── websocket/handler.py
  │     └── core/security.py
  └── static/

routers → models → core/database.py
routers → schemas
routers → core/auth_deps
core/auth_deps → core/security, core/database, core/config, core/exceptions, models
```

### Circular dependencies

**None detected.** The dependency flow is unidirectional: `main.py` → `routers` → `core`/`models`/`schemas`.

### Imports map

```
core/
  config.py        → pydantic-settings, pathlib
  database.py      → core/config, sqlalchemy
  security.py      → core/config, models (lazy), jose, passlib
  auth_deps.py     → core/config, core/database, core/security, core/exceptions, models
  exceptions.py    → starlette.exceptions
  utils.py         → datetime
  uploads.py       → core/config, core/exceptions, aiofiles
  razorpay.py      → core/config, razorpay
  mail.py          → core/config, smtplib
  geo.py           → math
models/
  __init__.py      → core/database
schemas/
  __init__.py      → pydantic
routers/
  *                → core/*, models, schemas
websocket/
  handler.py       → core/security
generate_dummy_data.py → core/*, models, female_names_data
seed.py            → core/*, models
```

---

## 23. Component Responsibilities

| Component | Responsibility | Depends On |
|-----------|---------------|------------|
| `core/config.py` | Application configuration from env vars | pydantic-settings |
| `core/database.py` | DB engine, session factory, table creation, auto-migration | core/config |
| `core/security.py` | JWT creation/validation, password hashing, OTP logic | core/config, models |
| `core/auth_deps.py` | Dependency providers for auth (current user, admin, premium) | core/config, core/database, core/security, models |
| `core/exceptions.py` | Custom HTTP exception classes | starlette |
| `core/utils.py` | Age calculation utility | datetime |
| `core/uploads.py` | File validation and storage with aiofiles | core/config, core/exceptions, aiofiles |
| `core/razorpay.py` | Razorpay payment operations (order, verify, webhook) | core/config, razorpay |
| `core/mail.py` | SMTP email sending | core/config, smtplib |
| `core/geo.py` | Haversine distance calculation | math |
| `models/__init__.py` | 15 SQLAlchemy ORM models | core/database |
| `schemas/__init__.py` | 66 Pydantic request/response models | pydantic |
| `services/` | **Empty — no implementation** | — |
| `middleware/rate_limit.py` | IP-based rate limiting (100 req/60s) | fastapi, starlette |
| `routers/auth.py` | Auth endpoints (OTP, login, register, refresh) | core/*, models, schemas |
| `routers/profile.py` | Profile management, photos, languages | core/*, core/uploads, models, schemas |
| `routers/discovery.py` | Discovery feed, swipes, match creation | core/*, core/geo, models, schemas |
| `routers/matches.py` | Matches listing, messaging, women-first gate | core/*, models, schemas |
| `routers/notifications.py` | Notification queries, read/unread, push token | core/*, models, schemas |
| `routers/reports.py` | Report, block, unblock | core/*, models, schemas |
| `routers/family.py` | Family share create/revoke/view | core/*, models, schemas |
| `routers/verification.py` | Phone/photo verification | core/*, models, schemas |
| `routers/preferences.py` | Discovery preferences CRUD | core/*, models, schemas |
| `routers/subscriptions.py` | Plans, payment orders, verification, webhooks | core/*, core/razorpay, models, schemas |
| `routers/admin.py` | Full admin CRUD, stats, dummy data | core/*, models, schemas, generate_dummy_data |
| `websocket/handler.py` | WebSocket connections and typing relay | core/security |
| `seed.py` | Default admin user and plans creation | core/*, models |
| `generate_dummy_data.py` | Dummy data generation (SSE streaming) | core/*, models, female_names_data |
| `main.py` | App factory, middleware, router registration, static mounts | all routers, middleware, core/* |

---

## 24. API Summary

See [Section 5: API Layer](#5-api-layer) for the complete endpoint table with all 60+ endpoints.

---

## 25. Configuration Reference

| Name | Default | Required | Purpose | Used in |
|------|---------|----------|---------|---------|
| `APP_NAME` | `Brownies Dating App` | No | App title in OpenAPI docs | `main.py` |
| `API_V1_PREFIX` | `/api/v1` | No | All API route prefix | All routers |
| `DEBUG` | `false` | No | Shows OTP in response when true | `routers/auth.py` |
| `DATABASE_URL` | `postgresql+asyncpg://brownies:brownies@localhost:5432/brownies` | **Yes** | DB connection string | `core/database.py` |
| `DATABASE_ECHO` | `false` | No | SQL query logging | `core/database.py` |
| `DB_POOL_SIZE` | `20` | No | Asyncpg pool size | `core/database.py` |
| `DB_MAX_OVERFLOW` | `10` | No | Max pool overflow | `core/database.py` |
| `DB_POOL_RECYCLE` | `3600` | No | Connection recycle time (s) | `core/database.py` |
| `JWT_SECRET` | Insecure default | **Yes** | JWT HMAC secret key | `core/security.py` |
| `JWT_ALGORITHM` | `HS256` | No | JWT signing algorithm | `core/security.py` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | No | Access token lifetime | `core/security.py` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | No | Refresh token lifetime | `core/security.py` |
| `OTP_BYPASS` | `""` | No | Fixed OTP bypass value | `core/security.py` |
| `OTP_LENGTH` | `6` | No | OTP digit count | `core/security.py` |
| `OTP_EXPIRE_SECONDS` | `300` | No | OTP validity period | `core/security.py`, `routers/auth.py` |
| `OTP_RATE_LIMIT` | `3` | No | Max OTP requests per window | `core/security.py` |
| `OTP_RATE_WINDOW_MINUTES` | `10` | No | OTP rate limit window | `core/security.py` |
| `TWILIO_ACCOUNT_SID` | `""` | No | **UNUSED** (dead config) | `core/config.py` only |
| `TWILIO_AUTH_TOKEN` | `""` | No | **UNUSED** (dead config) | `core/config.py` only |
| `TWILIO_PHONE` | `""` | No | **UNUSED** (dead config) | `core/config.py` only |
| `UPLOAD_DIR` | `data/uploads` | No | File upload root directory | `core/uploads.py`, `main.py` |
| `MAX_PHOTO_SIZE_MB` | `10` | No | Max photo file size | `core/uploads.py` |
| `MAX_PHOTOS_PER_USER` | `6` | No | Max photos per user | `routers/profile.py`, `routers/admin.py` |
| `DAILY_LIKES_FREE` | `50` | No | Default daily like limit | `routers/discovery.py` |
| `DAILY_SUPER_LIKES_FREE` | `1` | No | Default daily super like limit | `routers/discovery.py` |
| `FAMILY_SHARE_EXPIRE_DAYS` | `7` | No | Share link expiry in days | `routers/family.py` |
| `FAMILY_SHARE_TOKEN_LENGTH` | `32` | No | Share token random bytes | `routers/family.py` |
| `SMTP_HOST` | `""` | No | SMTP server address | `core/mail.py` |
| `SMTP_PORT` | `587` | No | SMTP port | `core/mail.py` |
| `SMTP_USER` | `""` | No | SMTP username | `core/mail.py` |
| `SMTP_PASSWORD` | `""` | No | SMTP password | `core/mail.py` |
| `SMTP_FROM_NAME` | `Brownies` | No | Email sender name | `core/mail.py` |
| `NOTIFY_EMAIL` | `""` | No | Email for admin notifications | `main.py` |
| `RAZORPAY_KEY_ID` | `""` | No | Razorpay API key ID | `core/razorpay.py`, `routers/subscriptions.py` |
| `RAZORPAY_KEY_SECRET` | `""` | No | Razorpay API secret | `core/razorpay.py` |
| `RAZORPAY_WEBHOOK_SECRET` | `""` | No | Razorpay webhook signing secret | `core/razorpay.py` |
| `ADMIN_PHONES` | `["0000000000"]` | No | Admin phone number whitelist | `core/auth_deps.py` |
| `CORS_ORIGINS` | `""` | No | Comma-separated allowed origins | `core/config.py`, `main.py` |

---

## 26. Technical Debt

### Duplicated code

1. **Sorting logic** — Every admin endpoint reimplements sort-to-column mapping with `sort_map` dicts and inline ordering. This pattern appears 7+ times.
2. **Pagination** — Manual offset/limit pagination is repeated in every admin endpoint, without a shared helper.
3. **Search filtering** — Similar `ilike` search patterns duplicated across admin endpoints.
4. **Duplicate OTP stores** — `store_otp`/`verify_otp` (sync, in-memory) and `store_otp_async`/`verify_otp_async` (async, DB-backed) exist in parallel.

### Large modules

1. **`routers/admin.py`** — 1,352 lines with 35+ endpoint functions. No submodules or delegation.
2. **`models/__init__.py`** — 216 lines, all 15 models in a single file.
3. **`schemas/__init__.py`** — 654 lines, all 66 Pydantic models in a single file.

### Tight coupling

1. **Router handlers directly access SQLAlchemy models** — No repository or service abstraction.
2. **Business logic embedded in endpoints** — Discovery feed filtering, match creation, payment verification all in router files.
3. **Direct imports from sibling routers** — `routers/subscriptions.py` imports `verify_otp_async` from `core.security` (correct) but the web-order flow creates users inline with raw SQLAlchemy calls.
4. **Authentication coupled to User model** — `get_current_user` returns `User` ORM instances directly, not DTOs.

### Code smells

1. **Empty `services/` directory** — Exists but never used.
2. **Twilio configured but not used** — Dead configuration and unused dependency.
3. **`model_config = {"from_attributes": True}`** in Pydantic models — Uses dict style instead of `model_config = ConfigDict(from_attributes=True)`.
4. **Inconsistent Pydantic usage** — Some response models use `model_validate()`, others use direct constructor.
5. **No type hints on some functions** — e.g., `generate_dummy_data()` has no return type annotation.
6. **Hardcoded JSON keys** in admin HTML (2,043 lines of inline JS).

### Unused code

1. Twilio SDK (installed but no code references it).
2. `websockets` package (installed but WebSocket uses FastAPI's built-in support, not the `websockets` library directly).

### Deprecated patterns

1. **Sync OTP store** (`otp_store` dict) — The async DB-backed version exists; the sync version appears unused in production code paths but remains in `core/security.py`.

---

## 27. Strengths

1. **Well-structured modular routers** — Clean separation of API concerns with 11 router files.
2. **Comprehensive admin panel** — Full CRUD for all entities, stats, import/export, dummy data generation with SSE streaming.
3. **Auto-migration on startup** — Tables and columns are automatically created/migrated, enabling rapid development.
4. **Feature-gated subscription model** — Premium features are properly gated using `get_premium_user` dependency injection.
5. **Women-first messaging** — Implemented as a business rule with clear gate logic.
6. **Proper match constraint** — `user1_id < user2_id` check constraint prevents duplicate matches and ensures consistent ordering.
7. **Runtime-configurable limits** — App settings can be updated via admin API without restart.
8. **Web checkout path** — Supports non-JWT payment flow for users who haven't registered yet.
9. **Comprehensive test coverage on utilities** — Good unit tests for security, geo, exceptions, and utils.
10. **Docker health checks** — Both database and app have health checks with proper depends_on ordering.

---

## 28. Improvement Opportunities

### High Impact

1. **Implement a service layer** — Move business logic from router handlers into service classes. The empty `services/` directory is ready for this.
2. **Add repository layer** — Abstract database queries behind repository classes to reduce tight coupling and improve testability.
3. **Integrate actual OTP delivery** — Use Twilio (already installed) or an alternative SMS provider to actually send OTPs to phones.
4. **Add structured logging** — Implement logging with levels, request IDs, and structured output (JSON) for production observability.
5. **Add Alembic for migrations** — Replace auto-migration with proper versioned migrations for production schema management.
6. **Address security issues** — Remove hardcoded default JWT secret in production, add CSRF protection, add request size limits, add security headers.
7. **Remove DEBUG OTP exposure** — Disable OTP-in-response or gate it behind an explicit developer-only flag.

### Medium Impact

8. **Extract admin router** — Split 1,352-line admin router into submodules (admin_users.py, admin_matches.py, admin_plans.py, etc.).
9. **Extract models and schemas** — Split single-file models and schemas into per-entity modules.
10. **Add pagination helper** — Create a shared pagination utility to eliminate duplicated offset/limit logic.
11. **Add API versioning** — Add `/api/v2/` or use header-based versioning to enable safe API evolution.
12. **Offload blocking I/O** — Use `run_in_executor()` for SMTP, bcrypt, and Razorpay SDK calls.
13. **Add request validation middleware** — Centralize input validation with request body size limits and content-type checking.
14. **Add dependency scanning** — Add `pip-audit` or Dependabot for vulnerability scanning.

### Low Impact

15. **Move static files to a CDN** — Serve landing/login/checkout/admin pages from a dedicated frontend with CDN, not FastAPI StaticFiles.
16. **Add API documentation** — Enhance OpenAPI docs with better descriptions, examples, and response schemas.
17. **Add rate limiting to auth endpoints specifically** — OTP rate limiting exists per-phone but login brute-force protection is only IP-based.
18. **Add test coverage for routers** — Current tests skip database-dependent tests; add integration tests with a test database.
19. **Remove dead Twilio config** — Either implement Twilio or remove the dependency and env vars.
20. **Add CI/CD pipeline** — No CI/CD files (`.github/workflows/`, etc.) are present.

---

## 29. Appendix

### Package inventory (`requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | * | Web framework |
| `uvicorn[standard]` | * | ASGI server |
| `sqlalchemy` | * | ORM |
| `pydantic` | * | Data validation |
| `pydantic-settings` | * | Environment configuration |
| `python-jose[cryptography]` | * | JWT encoding/decoding |
| `passlib[bcrypt]` | * | Password hashing |
| `bcrypt<4.1` | * | bcrypt implementation (pinned) |
| `python-multipart` | * | File upload parsing |
| `aiofiles` | * | Async file I/O |
| `websockets` | * | WebSocket support |
| `twilio` | * | **NOT USED** (installed but no code references) |
| `httpx` | * | HTTP client (potential future use) |
| `aiohttp` | * | Async HTTP client (potential future use) |
| `asyncpg` | * | PostgreSQL async driver |
| `razorpay` | * | Payment gateway |
| `pytest` | * | Test framework |
| `pytest-asyncio` | * | Async test support |
| `pytest-cov` | * | Test coverage |

*No version pins except `bcrypt<4.1`.*

### Technology stack summary

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Framework | FastAPI |
| Server | Uvicorn |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 (async) |
| DB Driver | asyncpg |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Payments | Razorpay |
| Email | smtplib (stdlib) |
| WebSocket | FastAPI built-in |
| Configuration | pydantic-settings |
| Container | Docker (python:3.12-slim) |
| Tests | pytest + pytest-asyncio + pytest-cov |
| Static Pages | Raw HTML/CSS/JS with Tailwind CDN |

### File sizes

| File | Lines |
|------|-------|
| `routers/admin.py` | 1,352 |
| `schemas/__init__.py` | 654 |
| `routers/discovery.py` | 300 |
| `routers/subscriptions.py` | 306 |
| `generate_dummy_data.py` | 277 |
| `routers/matches.py` | 274 |
| `static/admin/index.html` | 2,043 |
| `static/checkout/index.html` | 351 |
| `static/landing/index.html` | 780 |
| `static/login/index.html` | 184 |

---

*End of architecture document. Every statement above is based on static analysis of the codebase at `C:\Users\Admin\Documents\App Projects\Brownies-Backend\src\`, `tests\`, and `migrations\`.*
