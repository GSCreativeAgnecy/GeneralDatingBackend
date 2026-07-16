# Profile API

## Overview

The profile system has two API surfaces:

1. **v1** (`/profile`) — Flat user table with all columns
2. **v2** (`/profile/v2`) — Modular, section-based with lookup tables and versioning

## V2 Endpoints

### GET `/profile/v2/me`

Full profile with all sections and completion scores.

```json
{
    "user_id": 1,
    "first_name": "Rahul",
    "completion": {
        "overall_percentage": 72.5,
        "sections": [
            {"section_key": "basic_info", "completion_percentage": 100.0, "filled_count": 4, "total_count": 4}
        ]
    },
    "sections": [
        {
            "section_key": "basic_info",
            "section_name": "Basic Information",
            "fields": [
                {"field_key": "religion", "value": "hindu", "field_type": "lookup"}
            ]
        }
    ]
}
```

### PUT `/profile/v2/me/sections/{key}`

Update one section at a time. All values are validated against field definitions.

```json
{
    "fields": [
        {"field_id": 5, "value": "software_engineer"},
        {"field_id": 6, "value": "1500000", "visibility": "matches_only"}
    ]
}
```

### GET `/profile/v2/me/completion`

Weighted completion percentage per section.

### GET `/profile/v2/me/history`

Audit trail of all profile value changes with old/new values and timestamps.

## Admin Endpoints

Admins can create, update, reorder, and delete field definitions and sections. See `/profile/v2/admin/*` endpoints and `/profile/v2/admin/lookup/{table}` for managing dropdown values.

## Lookup Tables

Standardized dropdown values for religions, castes, occupations, educations, and languages. Managed via `/profile/v2/admin/lookup/{table}`.

```json
// PUT /profile/v2/admin/lookup/occupations
{"value": "data_scientist", "label": "Data Scientist", "display_order": 11}
```

Adding a lookup value automatically makes it available in all fields that reference that lookup table.
