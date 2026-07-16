from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth_deps import get_current_admin, get_current_user
from core.config import settings
from core.database import get_db
from models import User
from schemas.profile_v2 import (
    BulkUpdateProfileRequest,
    EditableFieldsOut,
    FullProfileOut,
    LookupItemOut,
    LookupItemUpsert,
    ModerationAction,
    ProfileCompletionOut,
    ProfileFieldDefinitionOut,
    ProfileFieldDefinitionPatch,
    ProfileFieldDefinitionUpsert,
    ProfileSectionOut,
    ProfileSectionUpsert,
    ProfileValueVersionOut,
    SearchableFieldItem,
    SearchableFieldsOut,
    UpdateSectionRequest,
    ValidationMetadataOut,
)
from services.profile_v2 import (
    ProfileFieldCache,
    create_field_definition,
    create_section,
    delete_field_definition,
    delete_lookup_item,
    get_editable_fields,
    get_full_profile,
    get_lookup_options,
    get_profile_completion,
    get_searchable_fields,
    get_user_section,
    get_validation_metadata,
    get_value_history,
    moderate_field_value,
    rebuild_search_index_for_user,
    update_field_definition,
    update_user_section,
    upsert_lookup_item,
)

router = APIRouter(
    prefix=f"{settings.API_V1_PREFIX}/profile/v2",
    tags=["profile-v2"],
)

# ── User: Full Profile ──


@router.get("/me", response_model=FullProfileOut)
async def my_full_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_full_profile(user.id, db)


# ── User: Section CRUD ──


@router.get("/me/sections/{section_key}")
async def my_section(
    section_key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_section(user.id, section_key, db)


@router.put("/me/sections/{section_key}")
async def update_my_section(
    section_key: str,
    req: UpdateSectionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await update_user_section(
        user.id, section_key, req.model_dump()["fields"], changed_by=user.id, db=db
    )


@router.put("/me/bulk")
async def bulk_update(
    req: BulkUpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for sec in req.sections:
        await update_user_section(
            user.id, sec.section_key, sec.fields, changed_by=user.id, db=db,
        )
    return await get_full_profile(user.id, db)


# ── User: Completion ──


@router.get("/me/completion", response_model=ProfileCompletionOut)
async def my_completion(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_profile_completion(user.id, db)


# ── User: Value history ──


@router.get("/me/history/{field_id}", response_model=list[ProfileValueVersionOut])
async def my_value_history(
    field_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_value_history(user.id, field_id, db)


@router.get("/me/history", response_model=list[ProfileValueVersionOut])
async def my_full_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_value_history(user.id, None, db)


# ── Public: Section & field definitions ──


@router.get("/sections", response_model=list[ProfileSectionOut])
async def list_sections(db: AsyncSession = Depends(get_db)):
    cache = ProfileFieldCache()
    sections = await cache.get_all_sections(db)
    return [
        ProfileSectionOut(
            id=s.id, key=s.key, name=s.name, name_hi=s.name_hi,
            description=s.description, icon=s.icon, display_order=s.display_order,
            completion_weight=s.completion_weight, visibility_rule=s.visibility_rule,
            min_app_version=s.min_app_version, is_active=s.is_active, is_system=s.is_system,
            fields=[
                ProfileFieldDefinitionOut.model_validate(f)
                for f in (s.fields or []) if f.is_active
            ],
        )
        for s in sections
    ]


@router.get("/sections/{section_key}", response_model=ProfileSectionOut)
async def get_section(section_key: str, db: AsyncSession = Depends(get_db)):
    sections = await ProfileFieldCache.get_all_sections(db)
    section = next((s for s in sections if s.key == section_key), None)
    if not section:
        from core.exceptions import NotFoundException
        raise NotFoundException(f"Section '{section_key}' not found")
    return ProfileSectionOut(
        id=section.id, key=section.key, name=section.name, name_hi=section.name_hi,
        description=section.description, icon=section.icon,
        display_order=section.display_order,
        completion_weight=section.completion_weight,
        visibility_rule=section.visibility_rule,
        min_app_version=section.min_app_version,
        is_active=section.is_active, is_system=section.is_system,
        fields=[
            ProfileFieldDefinitionOut.model_validate(f)
            for f in (section.fields or []) if f.is_active
        ],
    )


@router.get("/editable-fields")
async def editable_fields(db: AsyncSession = Depends(get_db)):
    return {"sections": await get_editable_fields(db)}


@router.get("/searchable-fields", response_model=SearchableFieldsOut)
async def searchable_fields_list(db: AsyncSession = Depends(get_db)):
    return {"fields": await get_searchable_fields(db)}


@router.get("/validation-metadata", response_model=list[ValidationMetadataOut])
async def validation_metadata_list(db: AsyncSession = Depends(get_db)):
    return await get_validation_metadata(db)


# ── Admin: Sections ──


@router.post("/admin/sections", response_model=ProfileSectionOut)
async def admin_create_section(
    req: ProfileSectionUpsert,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    section = await create_section(db, req.model_dump(), created_by=admin.phone_number)
    return ProfileSectionOut.model_validate(section)


@router.delete("/admin/sections/{section_id}")
async def admin_delete_section(
    section_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from models.profile import ProfileSection
    section = (await db.execute(select(ProfileSection).where(ProfileSection.id == section_id))).scalar_one_or_none()
    if not section:
        from core.exceptions import NotFoundException
        raise NotFoundException("Section not found")
    await db.delete(section)
    await db.flush()
    ProfileFieldCache.invalidate()
    return {"success": True, "message": f"Section '{section.key}' deleted"}


# ── Admin: Field definitions ──


@router.post("/admin/fields", response_model=ProfileFieldDefinitionOut)
async def admin_create_field(
    req: ProfileFieldDefinitionUpsert,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    fd = await create_field_definition(db, req.model_dump(), created_by=admin.phone_number)
    return ProfileFieldDefinitionOut.model_validate(fd)


@router.put("/admin/fields/{field_id}", response_model=ProfileFieldDefinitionOut)
async def admin_update_field(
    field_id: int,
    req: ProfileFieldDefinitionUpsert,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    fd = await update_field_definition(field_id, req.model_dump(), db)
    return ProfileFieldDefinitionOut.model_validate(fd)


@router.patch("/admin/fields/{field_id}", response_model=ProfileFieldDefinitionOut)
async def admin_patch_field(
    field_id: int,
    req: ProfileFieldDefinitionPatch,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    fd = await update_field_definition(field_id, req.model_dump(exclude_unset=True), db)
    return ProfileFieldDefinitionOut.model_validate(fd)


@router.delete("/admin/fields/{field_id}")
async def admin_delete_field(
    field_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await delete_field_definition(field_id, db)
    return {"success": True, "message": "Field definition deleted"}


@router.get("/admin/fields", response_model=list[ProfileFieldDefinitionOut])
async def admin_list_all_fields(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProfileFieldDefinition).order_by(
            ProfileFieldDefinition.section_id,
            ProfileFieldDefinition.display_order,
        )
    )
    return [ProfileFieldDefinitionOut.model_validate(f) for f in result.scalars().all()]


# ── Admin: Moderation ──


@router.post("/admin/moderate/{user_id}")
async def admin_moderate_value(
    user_id: int,
    req: ModerationAction,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    fv = await moderate_field_value(user_id, req.field_id, req.action, admin.id, db)
    return {
        "success": True,
        "field_id": fv.field_id,
        "status": fv.moderation_status,
    }


# ── Admin: Search index rebuild ──


@router.post("/admin/rebuild-search/{user_id}")
async def admin_rebuild_search(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    count = await rebuild_search_index_for_user(user_id, db)
    return {"success": True, "indexed_fields": count}


@router.post("/admin/rebuild-search-all")
async def admin_rebuild_search_all(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User.id))
    total = 0
    for (uid,) in result.all():
        total += await rebuild_search_index_for_user(uid, db)
    return {"success": True, "total_indexed_fields": total}


# ── Admin: Lookup tables ──

_LOOKUP_NAMES = {"religions", "castes", "occupations", "educations", "languages"}


@router.get("/admin/lookup/{table_name}", response_model=list[LookupItemOut])
async def admin_list_lookup(
    table_name: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if table_name not in _LOOKUP_NAMES:
        from core.exceptions import ValidationException
        raise ValidationException(f"Unknown lookup table: {table_name}")
    return await get_lookup_options(table_name, db)


@router.put("/admin/lookup/{table_name}", response_model=LookupItemOut)
async def admin_upsert_lookup(
    table_name: str,
    req: LookupItemUpsert,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if table_name not in _LOOKUP_NAMES:
        from core.exceptions import ValidationException
        raise ValidationException(f"Unknown lookup table: {table_name}")
    return await upsert_lookup_item(table_name, req.model_dump(), db)


@router.delete("/admin/lookup/{table_name}/{value}")
async def admin_delete_lookup(
    table_name: str,
    value: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if table_name not in _LOOKUP_NAMES:
        from core.exceptions import ValidationException
        raise ValidationException(f"Unknown lookup table: {table_name}")
    await delete_lookup_item(table_name, value, db)
    return {"success": True, "message": f"Deleted '{value}' from {table_name}"}
