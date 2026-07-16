# Migrations

## Migration Strategy

The project uses a **hybrid migration approach**:

1. **Auto-migration on startup**: `init_db()` in `src/core/database.py` runs `Base.metadata.create_all()` to create missing tables, then calls `migrate_missing_columns()` to add any columns defined in the ORM model that don't exist in the database.

2. **Manual SQL migrations**: Located in `migrations/` directory, numbered sequentially. Run manually with `psql`.

## Migration Files

| File | Purpose |
|------|---------|
| `001_add_performance_indexes.sql` | Production indexes for discovery, swipes, messages, notifications |
| `002_add_user_profile_fields.sql` | Added extended profile fields to users table |
| `003_modular_profile_system.sql` | Modular profile system: lookup tables, sections, field definitions, values, versioning, search index |

## Running Migrations

```bash
# Production
psql -d ardhang -f migrations/001_add_performance_indexes.sql
psql -d ardhang -f migrations/003_modular_profile_system.sql

# Verify
psql -d ardhang -c "\dt profile_*"
```

## Auto-Migration Detail

`migrate_missing_columns()` inspects the live database schema and compares it against SQLAlchemy model metadata. For any column missing from a table:

1. Extracts the column type, nullability, and default value
2. Constructs an `ALTER TABLE ... ADD COLUMN` statement
3. Executes it against the database

**Note**: Auto-migration only adds columns — it never removes or modifies existing ones. Use manual migrations for schema changes that require data transformation.

## Best Practices

- Always write **reversible** migrations (include a `-- ROLLBACK` comment or separate down script)
- Wrap migrations in `BEGIN; ... COMMIT;` transactions
- Test migrations on a staging database first
- Include `IF NOT EXISTS` / `IF EXISTS` guards for idempotency
- Never include environment-specific data in migrations
