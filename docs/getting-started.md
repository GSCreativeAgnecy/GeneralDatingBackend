# Getting Started

## Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Docker & Docker Compose (optional)

## Quick Start (Docker)

```bash
# Clone the repository
git clone <repo-url>
cd Ardhang-Matrimony-Backend

# Copy environment file
cp .env.example .env
# Edit .env with your values, especially JWT_SECRET

# Start services
docker-compose up -d
```

The API will be available at `http://localhost:8000`.

## Quick Start (Local)

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Ensure PostgreSQL is running and create the database
createdb ardhang

# Copy and configure environment
cp .env.example .env

# Run the application
cd src
python seed.py          # Creates admin account + default data
uvicorn main:app --reload
```

## Default Admin Credentials

> Change these immediately in production.

| Field | Value |
|-------|-------|
| Phone | `0000000000` |
| Password | `admin123` |

## Environment Variables

See `.env.example` for the full list. Critical variables:

| Variable | Purpose | Required |
|----------|---------|----------|
| `JWT_SECRET` | Token signing key (min 32 chars) | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `ADMIN_PHONES` | Comma-separated admin phone numbers | Yes |
| `CORS_ORIGINS` | Allowed frontend origins | Production |
| `SMTP_HOST` | Email server | Optional |
| `RAZORPAY_KEY_ID` | Payment processor | Optional |

## Health Check

```bash
curl http://localhost:8000/api/v1/health
# {"status": "ok", "app": "Ardhang Matrimony"}
```
