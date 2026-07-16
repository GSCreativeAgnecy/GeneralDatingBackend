# Database Schema

## Core Tables

### users

Primary user identity and authentication table.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER (PK) | Auto-increment |
| phone_number | VARCHAR | Unique, indexed |
| email | VARCHAR | Unique, nullable |
| password_hash | VARCHAR | bcrypt |
| first_name | VARCHAR | Required |
| last_name | VARCHAR | Default "" |
| date_of_birth | VARCHAR | YYYY-MM-DD format |
| gender | VARCHAR | Required |
| city | VARCHAR | Indexed |
| bio | TEXT | Nullable |
| intent | VARCHAR | Default "lets_see" |
| is_premium | BOOLEAN | Default false |
| is_active | BOOLEAN | Default true |
| profile_complete | BOOLEAN | Default false |

### profile_sections

Groups profile fields into logical sections.

| Column | Type | Notes |
|--------|------|-------|
| key | VARCHAR | Unique (e.g. "lifestyle") |
| name | VARCHAR | Display name |
| icon | VARCHAR | CSS icon identifier |
| completion_weight | FLOAT | Weight in completion score |
| is_system | BOOLEAN | System-created vs user-created |

### profile_field_definitions

Metadata about each profile field.

| Column | Type | Notes |
|--------|------|-------|
| key | VARCHAR | Unique (e.g. "religion") |
| field_type | VARCHAR | text, select, lookup, integer, etc. |
| lookup_table | VARCHAR | References lookup tables for dropdown options |
| validation_rules | JSONB | min/max, regex, allowed values |
| default_visibility | VARCHAR | public, matches_only, premium_only, private, hidden |
| completion_weight | FLOAT | Contribution to profile completion |
| pii | BOOLEAN | Personally identifiable information flag |
| encrypt_at_rest | BOOLEAN | Requires encryption |

### profile_field_values

User's actual profile data (EAV pattern).

| Column | Type | Notes |
|--------|------|-------|
| user_id | INTEGER (FK) | References users |
| field_id | INTEGER (FK) | References profile_field_definitions |
| value | TEXT | The stored value |
| visibility | VARCHAR | User-overridable visibility |
| moderation_status | VARCHAR | pending, approved, rejected |

### profile_value_versions

Audit trail for all profile changes.

| Column | Type | Notes |
|--------|------|-------|
| user_id | INTEGER | Whose profile |
| field_id | INTEGER | Which field |
| old_value | TEXT | Before |
| new_value | TEXT | After |
| changed_by | INTEGER | Who made the change |
| change_source | VARCHAR | user, admin, system |

## Relationship Map

```
users ──< user_photos
users ──< user_languages
users ──< user_preferences (1:1)
users ──< swipes (as swiper)
users ──< swipes (as swiped)
users ──< matches (as user1 or user2)
matches ──< messages
users ──< profile_field_values
profile_field_definitions ──< profile_field_values
profile_sections ──< profile_field_definitions
users ──< subscriptions
plans ──< subscriptions
users ──< profile_value_versions
```

## Performance Indexes

Run `migrations/001_add_performance_indexes.sql` for recommended production indexes covering discovery feed, swipe queries, message retrieval, notification lookups, and block/report filtering.
