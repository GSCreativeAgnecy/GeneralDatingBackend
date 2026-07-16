import re

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_missing_columns)


def _migrate_missing_columns(conn) -> None:
    inspector = inspect(conn)
    for table_name, table in Base.metadata.tables.items():
        if not inspector.has_table(table_name):
            continue
        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name not in existing_columns:
                _safe_add_column(conn, table_name, column)


def _safe_add_column(conn, table_name: str, column) -> None:
    if not _SAFE_IDENTIFIER.match(table_name) or not _SAFE_IDENTIFIER.match(column.name):
        print(f"Skipping unsafe column migration: {table_name}.{column.name}")
        return

    col_type = column.type.compile(dialect=conn.dialect)
    nullable = "NULL" if column.nullable else "NOT NULL"
    default_clause = ""
    if column.default is not None and hasattr(column.default, "arg"):
        # Safe: the arg is a literal value or expression handled by SQLAlchemy
        default_clause = f" DEFAULT {column.default.arg}"

    sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} {nullable}{default_clause}"
    try:
        conn.execute(text(sql))
        print(f"Added column {table_name}.{column.name}")
    except Exception as e:
        print(f"Failed to add {table_name}.{column.name}: {e}")
