# Coding Standards

## Python

- **PEP 8** compliance
- Type hints everywhere: function signatures, return types, class attributes
- Use `from __future__ import annotations` for forward references
- Docstrings for public functions and classes (Google style)

## Naming

| Convention | Usage |
|-----------|-------|
| `snake_case` | Variables, functions, methods, modules, columns |
| `PascalCase` | Classes, Pydantic models |
| `UPPER_SNAKE` | Constants, enums |
| `_leading_underscore` | Private/internal |

## Imports

```python
# Standard library
import os
from datetime import datetime, timezone

# Third-party
from fastapi import APIRouter, Depends
from sqlalchemy import Column, select

# Local
from core.config import settings
from models import User
```

## Database

- Use `async def` with `await` for all database operations
- Use `select()` style queries (SQLAlchemy 2.0)
- Avoid raw SQL unless necessary (migrations excepted)
- Always use parameterized queries — never string interpolation
- Set cascade rules explicitly on relationships

## API

- All endpoints: `async def`
- Use Pydantic models for request/response — never dicts
- Validate early, fail fast
- Return proper HTTP status codes
- Error messages should not leak internal state

## Security

- Never log credentials, tokens, or OTPs
- Never hardcode secrets — use env vars or config
- Always validate and sanitize user input
- Use `secrets` module for cryptographic randomness
- Compare secrets with constant-time functions where available
