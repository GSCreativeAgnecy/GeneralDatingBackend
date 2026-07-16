from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import ConflictException, NotFoundException, ValidationException
from models.profile import (
    LookupCaste,
    LookupEducation,
    LookupLanguage,
    LookupOccupation,
    LookupReligion,
    ProfileFieldDefinition,
    ProfileFieldValue,
    ProfileSearchIndex,
    ProfileSection,
    ProfileValueVersion,
)

_VISIBILITY_LEVELS = {"public", "matches_only", "premium_only", "private", "hidden"}
_MODERATION_STATES = {"pending", "approved", "rejected", "under_review"}

_LOOKUP_TABLES = {
    "religions": LookupReligion,
    "castes": LookupCaste,
    "occupations": LookupOccupation,
    "educations": LookupEducation,
    "languages": LookupLanguage,
}


class ProfileFieldCache:
    _cache: dict[str, ProfileFieldDefinition] | None = None
    _sections_cache: list[ProfileSection] | None = None

    @classmethod
    def invalidate(cls) -> None:
        cls._cache = None
        cls._sections_cache = None

    @classmethod
    async def get_all_fields(cls, db: AsyncSession) -> dict[str, ProfileFieldDefinition]:
        if cls._cache is not None:
            return cls._cache
        result = await db.execute(
            select(ProfileFieldDefinition)
            .where(ProfileFieldDefinition.is_active == True)
            .order_by(ProfileFieldDefinition.display_order)
        )
        cls._cache = {f.key: f for f in result.scalars().all()}
        return cls._cache

    @classmethod
    async def get_all_sections(cls, db: AsyncSession) -> list[ProfileSection]:
        if cls._sections_cache is not None:
            return cls._sections_cache
        result = await db.execute(
            select(ProfileSection)
            .options(selectinload(ProfileSection.fields))
            .where(ProfileSection.is_active == True)
            .order_by(ProfileSection.display_order)
        )
        cls._sections_cache = list(result.unique().scalars().all())
        return cls._sections_cache


async def _resolve_lookup_options(lookup_table: str, db: AsyncSession) -> list[dict]:
    model = _LOOKUP_TABLES.get(lookup_table)
    if not model:
        return []
    result = await db.execute(
        select(model).where(model.is_active == True).order_by(model.display_order)
    )
    return [
        {"value": r.value, "label": r.label, "label_hi": getattr(r, "label_hi", None)}
        for r in result.scalars().all()
    ]


def _validate_field_value(field_def: ProfileFieldDefinition, value: Any) -> str | None:
    if value is None or value == "":
        if field_def.is_required:
            raise ValidationException(f"'{field_def.label}' is required")
        return None

    rules = field_def.validation_rules or {}
    value_str = str(value)

    ft = field_def.field_type

    if ft == "integer":
        try:
            int_val = int(value_str)
            if (rules.get("min_value") is not None and int_val < rules["min_value"]) or (
                rules.get("max_value") is not None and int_val > rules["max_value"]
            ):
                raise ValidationException(
                    f"'{field_def.label}' must be between {rules.get('min_value')} and {rules.get('max_value')}"
                )
        except (ValueError, TypeError):
            raise ValidationException(f"'{field_def.label}' must be a whole number")
        return value_str

    if ft == "decimal":
        try:
            float_val = float(value_str)
            if (rules.get("min_value") is not None and float_val < rules["min_value"]) or (
                rules.get("max_value") is not None and float_val > rules["max_value"]
            ):
                raise ValidationException(
                    f"'{field_def.label}' must be between {rules.get('min_value')} and {rules.get('max_value')}"
                )
        except (ValueError, TypeError):
            raise ValidationException(f"'{field_def.label}' must be a number")
        return value_str

    if ft == "boolean":
        truthy = {"true", "1", "yes", "on"}
        falsy = {"false", "0", "no", "off", ""}
        v = value_str.lower()
        if v in truthy:
            return "true"
        if v in falsy:
            return "false"
        raise ValidationException(f"'{field_def.label}' must be true or false")

    if ft in ("select", "radio", "multi-select", "checkbox", "lookup"):
        options = field_def.options or []
        allowed = {o.get("value", "") for o in options}
        if not allowed:
            return value_str
        vals = (
            [v.strip() for v in value_str.split(",")]
            if ft == "multi-select"
            else [value_str.strip()]
        )
        for v in vals:
            if v and v not in allowed:
                raise ValidationException(f"'{v}' is not a valid option for '{field_def.label}'")
        return value_str

    if ft == "date":
        try:
            datetime.strptime(value_str, "%Y-%m-%d")
        except ValueError:
            raise ValidationException(f"'{field_def.label}' must be a valid date (YYYY-MM-DD)")
        return value_str

    if (rules.get("min_length") is not None and len(value_str) < rules["min_length"]) or (
        rules.get("max_length") is not None and len(value_str) > rules["max_length"]
    ):
        raise ValidationException(
            f"'{field_def.label}' must be {rules.get('min_length')}-{rules.get('max_length')} characters"
        )

    if rules.get("regex"):
        try:
            if not re.match(rules["regex"], value_str):
                raise ValidationException(f"'{field_def.label}' does not match required format")
        except re.error:
            pass

    return value_str


def _resolve_options(field_def: ProfileFieldDefinition, lookup_opts: dict[str, list]) -> list[dict] | None:
    if field_def.lookup_table and field_def.lookup_table in lookup_opts:
        return lookup_opts[field_def.lookup_table]
    return field_def.options


def _field_value_item(
    field_def: ProfileFieldDefinition,
    raw: str | None,
    lookup_opts: dict[str, list],
) -> dict:
    return {
        "field_id": field_def.id,
        "field_key": field_def.key,
        "label": field_def.label,
        "field_type": field_def.field_type,
        "value": raw,
        "options": _resolve_options(field_def, lookup_opts),
        "is_required": field_def.is_required,
        "is_editable": field_def.is_editable,
        "visibility": "public",
        "moderation_status": "approved",
        "placeholder": field_def.placeholder,
        "help_text": field_def.help_text,
        "unit": field_def.unit,
        "completion_weight": field_def.completion_weight,
    }


async def _load_lookup_options(db: AsyncSession) -> dict[str, list]:
    result: dict[str, list] = {}
    for key, model in _LOOKUP_TABLES.items():
        rows = (await db.execute(select(model).where(model.is_active == True).order_by(model.display_order))).scalars().all()
        result[key] = [
            {"value": r.value, "label": r.label, "label_hi": getattr(r, "label_hi", None)}
            for r in rows
        ]
    return result


async def _record_version(
    db: AsyncSession,
    user_id: int,
    field_id: int,
    old: str | None,
    new: str | None,
    changed_by: int,
    source: str = "user",
) -> None:
    if old != new:
        db.add(
            ProfileValueVersion(
                user_id=user_id,
                field_id=field_id,
                old_value=old,
                new_value=new,
                changed_by=changed_by,
                change_source=source,
            )
        )


async def _sync_search_index(
    db: AsyncSession,
    user_id: int,
    field_def: ProfileFieldDefinition,
    value: str | None,
) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        delete(ProfileSearchIndex).where(
            ProfileSearchIndex.user_id == user_id,
            ProfileSearchIndex.field_key == field_def.key,
        )
    )
    if value is not None and value != "":
        numeric = None
        search_vector = None
        if field_def.field_type in ("integer", "decimal"):
            try:
                numeric = float(value)
            except (ValueError, TypeError):
                pass
        if field_def.field_type in ("text", "textarea", "select"):
            search_vector = text(
                "to_tsvector('english', :val)"
            ).bindparams(val=value)
        db.add(
            ProfileSearchIndex(
                user_id=user_id,
                field_key=field_def.key,
                value=value,
                numeric_value=numeric,
                search_vector=search_vector,
                updated_at=now,
            )
        )


# ── Public API ──


async def get_user_section(
    user_id: int,
    section_key: str,
    db: AsyncSession,
) -> dict:
    sections = await ProfileFieldCache.get_all_sections(db)
    section = next((s for s in sections if s.key == section_key), None)
    if not section:
        raise NotFoundException(f"Section '{section_key}' not found")

    field_defs = [f for f in (section.fields or []) if f.is_active and f.is_visible]
    if not field_defs:
        return {
            "section_id": section.id, "section_key": section.key,
            "section_name": section.name, "icon": section.icon,
            "display_order": section.display_order,
            "completion_weight": section.completion_weight,
            "fields": [],
        }

    field_ids = [f.id for f in field_defs]
    result = await db.execute(
        select(ProfileFieldValue).where(
            ProfileFieldValue.user_id == user_id,
            ProfileFieldValue.field_id.in_(field_ids),
        )
    )
    value_map = {v.field_id: v.value for v in result.scalars().all()}
    lookup_opts = await _load_lookup_options(db)

    return {
        "section_id": section.id, "section_key": section.key,
        "section_name": section.name, "icon": section.icon,
        "display_order": section.display_order,
        "completion_weight": section.completion_weight,
        "fields": [
            _field_value_item(fd, value_map.get(fd.id, fd.default_value), lookup_opts)
            for fd in field_defs
        ],
    }


async def update_user_section(
    user_id: int,
    section_key: str,
    field_updates: list[dict[str, Any]],
    changed_by: int,
    db: AsyncSession,
    change_source: str = "user",
) -> dict:
    all_fields = await ProfileFieldCache.get_all_fields(db)
    sections = await ProfileFieldCache.get_all_sections(db)

    section = next((s for s in sections if s.key == section_key), None)
    if not section:
        raise NotFoundException(f"Section '{section_key}' not found")

    existing_result = await db.execute(
        select(ProfileFieldValue).where(ProfileFieldValue.user_id == user_id)
    )
    existing_map = {v.field_id: v for v in existing_result.scalars().all()}

    now = datetime.now(timezone.utc)
    lookup_opts = await _load_lookup_options(db)

    for item in field_updates:
        field_id = item["field_id"]
        field_def = next(
            (f for f in (section.fields or []) if f.id == field_id),
            all_fields.get(str(field_id)),
        )
        if not field_def or not field_def.is_editable:
            continue

        raw_value = item.get("value")
        validated = _validate_field_value(field_def, raw_value)

        if field_def.lookup_table:
            opts = _resolve_options(field_def, lookup_opts)
            if opts and validated in {o["value"] for o in opts}:
                pass
            elif opts:
                raise ValidationException(
                    f"'{validated}' is not a valid option for '{field_def.label}'"
                )

        fv = existing_map.get(field_id)
        old_val = fv.value if fv else None
        if fv:
            fv.value = validated
            fv.updated_at = now
            if item.get("visibility") in _VISIBILITY_LEVELS:
                fv.visibility = item["visibility"]
        else:
            fv = ProfileFieldValue(
                user_id=user_id,
                field_id=field_id,
                value=validated,
                visibility=item.get("visibility", field_def.default_visibility),
                moderation_status="approved" if change_source == "user" else "under_review",
                updated_at=now,
            )
            db.add(fv)

        await _record_version(db, user_id, field_id, old_val, validated, changed_by, change_source)
        if field_def.is_searchable:
            await _sync_search_index(db, user_id, field_def, validated)

    await db.flush()
    return await get_user_section(user_id, section_key, db)


async def get_full_profile(user_id: int, db: AsyncSession) -> dict:
    from models import User

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    sections = await ProfileFieldCache.get_all_sections(db)
    lookup_opts = await _load_lookup_options(db)

    all_field_ids = [f.id for s in sections for f in (s.fields or []) if f.is_active and f.is_visible]
    result = await db.execute(
        select(ProfileFieldValue).where(
            ProfileFieldValue.user_id == user_id,
            ProfileFieldValue.field_id.in_(all_field_ids),
        )
    )
    value_map = {v.field_id: v.value for v in result.scalars().all()}

    completion_sections = []
    section_list = []
    total_weight = 0.0
    total_earned = 0.0

    for section in sections:
        sec_fields = []
        sec_total = 0.0
        sec_earned = 0.0
        for fd in (section.fields or []):
            if not fd.is_active or not fd.is_visible:
                continue
            raw = value_map.get(fd.id, fd.default_value)
            sec_total += fd.completion_weight
            if raw and raw != "":
                sec_earned += fd.completion_weight
            sec_fields.append(_field_value_item(fd, raw, lookup_opts))

        if sec_fields or section.is_active:
            section_list.append({
                "section_id": section.id, "section_key": section.key,
                "section_name": section.name, "icon": section.icon,
                "display_order": section.display_order,
                "completion_weight": section.completion_weight,
                "fields": sec_fields,
            })
        if sec_total > 0:
            sec_completion = round((sec_earned / sec_total) * 100, 1)
        else:
            sec_completion = 100.0
        completion_sections.append({
            "section_key": section.key,
            "section_name": section.name,
            "completion_percentage": sec_completion,
            "filled_count": sum(1 for _ in ()),  # placeholder — computed above
            "total_count": sum(1 for _ in ()),  # placeholder
            "weighted_score": sec_earned,
        })
        total_weight += sec_total
        total_earned += sec_earned

    overall = round((total_earned / total_weight) * 100, 1) if total_weight > 0 else 0.0

    return {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name or "",
        "date_of_birth": user.date_of_birth,
        "gender": user.gender,
        "city": user.city,
        "bio": user.bio,
        "intent": user.intent,
        "profile_complete": user.profile_complete,
        "completion": {
            "overall_percentage": overall,
            "sections": completion_sections,
        },
        "sections": section_list,
    }


async def get_profile_completion(user_id: int, db: AsyncSession) -> dict:
    sections = await ProfileFieldCache.get_all_sections(db)
    all_field_ids = [f.id for s in sections for f in (s.fields or []) if f.is_active and f.is_visible]
    result = await db.execute(
        select(ProfileFieldValue).where(
            ProfileFieldValue.user_id == user_id,
            ProfileFieldValue.field_id.in_(all_field_ids),
        )
    )
    value_map = {v.field_id: v.value for v in result.scalars().all()}

    section_completions = []
    total_weight = 0.0
    total_earned = 0.0

    for section in sections:
        sec_weight = 0.0
        sec_earned = 0.0
        filled = 0
        total_fields = 0
        for fd in (section.fields or []):
            if not fd.is_active or not fd.is_visible:
                continue
            total_fields += 1
            sec_weight += fd.completion_weight
            raw = value_map.get(fd.id, fd.default_value)
            if raw and raw != "":
                sec_earned += fd.completion_weight
                filled += 1

        pct = round((sec_earned / sec_weight) * 100, 1) if sec_weight > 0 else 100.0
        section_completions.append({
            "section_key": section.key,
            "section_name": section.name,
            "completion_percentage": pct,
            "filled_count": filled,
            "total_count": total_fields,
            "weighted_score": round(sec_earned, 2),
        })
        total_weight += sec_weight
        total_earned += sec_earned

    return {
        "overall_percentage": round((total_earned / total_weight) * 100, 1) if total_weight > 0 else 0.0,
        "sections": section_completions,
    }


async def get_editable_fields(db: AsyncSession) -> list[dict]:
    sections = await ProfileFieldCache.get_all_sections(db)
    lookup_opts = await _load_lookup_options(db)
    result = []
    for section in sections:
        fields = []
        for fd in (section.fields or []):
            if fd.is_active and fd.is_editable:
                fields.append(_field_value_item(fd, fd.default_value, lookup_opts))
        if fields:
            result.append({
                "section_id": section.id, "section_key": section.key,
                "section_name": section.name, "icon": section.icon,
                "display_order": section.display_order,
                "completion_weight": section.completion_weight,
                "fields": fields,
            })
    return result


async def get_searchable_fields(db: AsyncSession) -> list[dict]:
    all_fields = await ProfileFieldCache.get_all_fields(db)
    lookup_opts = await _load_lookup_options(db)
    result = []
    for f in all_fields.values():
        if f.is_searchable and f.is_active:
            result.append({
                "key": f.key, "label": f.label, "field_type": f.field_type,
                "lookup_table": f.lookup_table,
                "options": _resolve_options(f, lookup_opts),
                "unit": f.unit,
            })
    return result


async def get_validation_metadata(db: AsyncSession) -> list[dict]:
    all_fields = await ProfileFieldCache.get_all_fields(db)
    return [
        {
            "field_id": f.id, "field_key": f.key,
            "validation_rules": f.validation_rules,
            "is_required": f.is_required, "field_type": f.field_type,
            "options": f.options,
        }
        for f in all_fields.values() if f.is_active
    ]


async def get_value_history(
    user_id: int,
    field_id: int | None,
    db: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    stmt = (
        select(ProfileValueVersion)
        .where(ProfileValueVersion.user_id == user_id)
    )
    if field_id:
        stmt = stmt.where(ProfileValueVersion.field_id == field_id)
    result = await db.execute(
        stmt.order_by(ProfileValueVersion.changed_at.desc()).limit(limit)
    )
    versions = result.scalars().all()

    field_ids = {v.field_id for v in versions if v.field_id}
    field_map = {}
    if field_ids:
        all_fields = await ProfileFieldCache.get_all_fields(db)
        field_map = {
            f.id: f for f in all_fields.values() if f.id in field_ids
        }

    return [
        {
            "id": v.id,
            "field_key": field_map[v.field_id].key if v.field_id in field_map else None,
            "field_label": field_map[v.field_id].label if v.field_id in field_map else None,
            "old_value": v.old_value,
            "new_value": v.new_value,
            "change_source": v.change_source,
            "changed_at": v.changed_at,
        }
        for v in versions
    ]


# ── Admin: Moderation ──


async def moderate_field_value(
    user_id: int,
    field_id: int,
    action: str,
    moderator_id: int,
    db: AsyncSession,
) -> ProfileFieldValue:
    result = await db.execute(
        select(ProfileFieldValue).where(
            ProfileFieldValue.user_id == user_id,
            ProfileFieldValue.field_id == field_id,
        )
    )
    fv = result.scalar_one_or_none()
    if not fv:
        raise NotFoundException("Field value not found")

    now = datetime.now(timezone.utc)
    if action == "approve":
        fv.moderation_status = "approved"
    elif action == "reject":
        fv.moderation_status = "rejected"
    elif action == "request_review":
        fv.moderation_status = "under_review"
    fv.moderated_by = moderator_id
    fv.moderated_at = now
    await db.flush()
    return fv


# ── Admin: CRUD ──


async def create_section(db: AsyncSession, section_data: dict, created_by: str = "admin") -> ProfileSection:
    existing = (await db.execute(select(ProfileSection).where(ProfileSection.key == section_data["key"]))).scalar_one_or_none()
    if existing:
        raise ConflictException(f"Section '{section_data['key']}' already exists")
    section = ProfileSection(**section_data, created_by=created_by)
    db.add(section)
    await db.flush()
    ProfileFieldCache.invalidate()
    return section


async def create_field_definition(db: AsyncSession, field_data: dict, created_by: str = "admin") -> ProfileFieldDefinition:
    existing = (await db.execute(select(ProfileFieldDefinition).where(ProfileFieldDefinition.key == field_data["key"]))).scalar_one_or_none()
    if existing:
        raise ConflictException(f"Field '{field_data['key']}' already exists")
    fd = ProfileFieldDefinition(**field_data, created_by=created_by)
    db.add(fd)
    await db.flush()
    ProfileFieldCache.invalidate()
    return fd


async def update_field_definition(field_id: int, patch: dict, db: AsyncSession) -> ProfileFieldDefinition:
    result = (await db.execute(select(ProfileFieldDefinition).where(ProfileFieldDefinition.id == field_id))).scalar_one_or_none()
    if not result:
        raise NotFoundException("Field definition not found")
    for k, v in patch.items():
        if v is not None:
            setattr(result, k, v)
    result.updated_at = datetime.now(timezone.utc)
    await db.flush()
    ProfileFieldCache.invalidate()
    return result


async def delete_field_definition(field_id: int, db: AsyncSession) -> None:
    result = (await db.execute(select(ProfileFieldDefinition).where(ProfileFieldDefinition.id == field_id))).scalar_one_or_none()
    if not result:
        raise NotFoundException("Field definition not found")
    await db.delete(result)
    await db.flush()
    ProfileFieldCache.invalidate()


async def rebuild_search_index_for_user(user_id: int, db: AsyncSession) -> int:
    all_fields = await ProfileFieldCache.get_all_fields(db)
    searchable = {k: f for k, f in all_fields.items() if f.is_searchable}
    if not searchable:
        return 0
    field_ids = [f.id for f in searchable.values()]
    result = await db.execute(
        select(ProfileFieldValue).where(
            ProfileFieldValue.user_id == user_id,
            ProfileFieldValue.field_id.in_(field_ids),
        )
    )
    values = result.scalars().all()
    await db.execute(delete(ProfileSearchIndex).where(ProfileSearchIndex.user_id == user_id))
    count = 0
    for fv in values:
        if not fv.value:
            continue
        fd = next((f for f in searchable.values() if f.id == fv.field_id), None)
        if not fd:
            continue
        await _sync_search_index(db, user_id, fd, fv.value)
        count += 1
    await db.flush()
    return count


# ── Lookup table admin ──


async def get_lookup_options(table_name: str, db: AsyncSession) -> list[dict]:
    model = _LOOKUP_TABLES.get(table_name)
    if not model:
        raise NotFoundException(f"Lookup table '{table_name}' not found")
    rows = (await db.execute(select(model).where(model.is_active == True).order_by(model.display_order))).scalars().all()
    return [{"value": r.value, "label": r.label, "label_hi": getattr(r, "label_hi", None), "display_order": r.display_order, "is_active": r.is_active} for r in rows]


async def upsert_lookup_item(table_name: str, item: dict, db: AsyncSession) -> dict:
    model = _LOOKUP_TABLES.get(table_name)
    if not model:
        raise NotFoundException(f"Lookup table '{table_name}' not found")
    existing = (await db.execute(select(model).where(model.value == item["value"]))).scalar_one_or_none()
    if existing:
        for k, v in item.items():
            setattr(existing, k, v)
    else:
        existing = model(**item)
        db.add(existing)
    await db.flush()
    return {"value": existing.value, "label": existing.label, "is_active": existing.is_active}


async def delete_lookup_item(table_name: str, value: str, db: AsyncSession) -> None:
    model = _LOOKUP_TABLES.get(table_name)
    if not model:
        raise NotFoundException(f"Lookup table '{table_name}' not found")
    result = (await db.execute(select(model).where(model.value == value))).scalar_one_or_none()
    if not result:
        raise NotFoundException(f"Item '{value}' not found")
    await db.delete(result)
    await db.flush()
