# Development Guide

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

## Environment

Copy `.env.example` to `.env` and configure:

```
DEBUG=true
JWT_SECRET=dev-secret-do-not-use-in-production-123456
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ardhang
ADMIN_PHONES=0000000000
OTP_BYPASS=123456
```

## Running

```bash
cd src
python seed.py           # Creates tables, admin user, default plans
uvicorn main:app --reload --port 8000
```

## Testing

```bash
pytest tests/ -v
```

Tests use `pytest-asyncio` with `asyncio_mode = auto`. No database is required for most tests — the conftest provides mock sessions.

## Code Style

- Follow PEP 8
- Type hints on all function signatures
- Use `async def` for all endpoint handlers
- Import order: stdlib → third-party → local
- Use Pydantic `model_validate()` for ORM → schema conversion
- Use `from_attributes = True` in Pydantic model config

## Project Conventions

### Models

- All models in `src/models/`
- `__tablename__` must be plural
- Use `Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))` for timestamps
- Relationships must specify cascade rules

### Routers

- One file per domain in `src/routers/`
- Router prefix uses `settings.API_V1_PREFIX`
- Auth dependencies: `get_current_user`, `get_current_admin`, `get_premium_user`
- Use `Depends(get_db)` for database sessions

### Schemas

- Request models named `*Request` (e.g. `SendOtpRequest`)
- Response models named `*Out` (e.g. `UserProfileOut`)
- Use `model_config = {"from_attributes": True}` for ORM compatibility
- Validation constraints via `Field()` and `@field_validator`

### Services

- Business logic in `src/services/`
- Caching via class-level variables with invalidation
- All functions accept `db: AsyncSession` as a parameter

## API Conventions

- JSON request/response bodies
- Snake_case field names
- Error responses: `{"detail": "message"}` with appropriate HTTP status
- Custom exceptions: `AuthException(401)`, `NotFoundException(404)`, etc.
- Pagination: `page` (1-indexed) and `per_page` query parameters
- Sorting: `sort_by` and `sort_dir` query parameters

## Database Migrations

- Auto-migration on startup: `init_db()` creates tables + adds missing columns
- Manual SQL migrations in `migrations/` directory
- No Alembic framework (yet)
- Always write reversible SQL migrations

## Logging

- Replace `print()` with Python `logging` module
- Use structured logging for production
- Log levels: DEBUG (dev), INFO (normal), WARNING (issues), ERROR (failures)
- Sanitize sensitive data before logging (passwords, tokens, OTPs)
