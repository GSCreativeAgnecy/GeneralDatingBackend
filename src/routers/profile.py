from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.config import settings
from core.database import get_db
from core.auth_deps import get_current_user
from core.exceptions import NotFoundException, ValidationException
from core.uploads import save_image_upload
from models import User, UserLanguage, UserPhoto
from schemas import (
    ReorderPhotosRequest,
    SetupProfileRequest,
    SuccessResponse,
    UpdateLanguagesRequest,
    UpdateProfileRequest,
    UserLanguageOut,
    UserPhotoOut,
    UserProfileOut,
)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/profile", tags=["profile"])


def profile_to_out(user: User) -> UserProfileOut:
    return UserProfileOut(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name or "",
        mother_tongue=user.mother_tongue or "",
        diet=user.diet or "",
        drinking=user.drinking or "",
        smoking=user.smoking or "",
        body_type=user.body_type or "",
        complexion=user.complexion or "",
        physical_status=user.physical_status or "",
        nakshatra=user.nakshatra or "",
        rashi=user.rashi or "",
        family_type=user.family_type or "",
        family_values=user.family_values or "",
        horoscope_match=user.horoscope_match,
        date_of_birth=user.date_of_birth,
        gender=user.gender,
        bio=user.bio,
        intent=user.intent,
        city=user.city,
        college=user.college,
        workplace=user.workplace,
        height_cm=user.height_cm,
        religion=user.religion,
        education=user.education,
        occupation=user.occupation,
        phone_verified=user.phone_verified,
        photo_verified=user.photo_verified,
        profile_complete=user.profile_complete,
        is_premium=user.is_premium,
        preferred_language=user.preferred_language,
        show_online_status=user.show_online_status,
        last_active=user.last_active,
        photos=[UserPhotoOut.model_validate(p) for p in (user.photos or [])],
        languages=[UserLanguageOut.model_validate(l) for l in (user.languages or [])],
        created_at=user.created_at,
    )


@router.get("/me", response_model=UserProfileOut)
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(
            joinedload(User.photos),
            joinedload(User.languages),
        ).where(User.id == user.id)
    )
    return profile_to_out(result.unique().scalar_one())


@router.post("/setup", response_model=UserProfileOut)
async def setup_profile(
    req: SetupProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.first_name = req.first_name
    user.date_of_birth = req.date_of_birth
    user.gender = req.gender
    user.intent = req.intent
    user.city = req.city
    user.bio = req.bio
    user.college = req.college
    user.workplace = req.workplace
    user.height_cm = req.height_cm
    user.religion = req.religion
    user.education = req.education
    user.occupation = req.occupation
    user.preferred_language = req.preferred_language
    user.profile_complete = True
    user.updated_at = datetime.now(timezone.utc)

    # Clear existing languages and set new
    result = await db.execute(select(UserLanguage).where(UserLanguage.user_id == user.id))
    for lang in result.scalars().all():
        await db.delete(lang)
    for lang in req.languages:
        db.add(UserLanguage(user_id=user.id, language=lang))

    await db.flush()
    result = await db.execute(
        select(User).options(
            joinedload(User.photos),
            joinedload(User.languages),
        ).where(User.id == user.id)
    )
    return profile_to_out(result.unique().scalar_one())


@router.patch("/me", response_model=UserProfileOut)
async def update_profile(
    req: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for key, value in req.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    await db.flush()
    result = await db.execute(
        select(User).options(
            joinedload(User.photos),
            joinedload(User.languages),
        ).where(User.id == user.id)
    )
    return profile_to_out(result.unique().scalar_one())


@router.post("/photos", response_model=UserPhotoOut)
async def upload_photo(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPhoto).where(UserPhoto.user_id == user.id)
    )
    existing = result.scalars().all()
    if len(existing) >= settings.MAX_PHOTOS_PER_USER:
        raise ValidationException(f"Maximum {settings.MAX_PHOTOS_PER_USER} photos allowed")

    photo_url = await save_image_upload(file, user.id)

    is_primary = len(existing) == 0
    photo = UserPhoto(
        user_id=user.id,
        photo_url=photo_url,
        is_primary=is_primary,
        sort_order=len(existing),
    )
    db.add(photo)
    await db.flush()
    if user.photo_verified and len(existing) >= 1:
        user.photo_verified = False
    return UserPhotoOut.model_validate(photo)


@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPhoto).where(UserPhoto.id == photo_id, UserPhoto.user_id == user.id)
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise NotFoundException("Photo not found")

    filepath = settings.UPLOAD_DIR / "photos" / Path(photo.photo_url).name
    if filepath.exists():
        filepath.unlink()

    await db.delete(photo)
    return SuccessResponse(message="Photo deleted")


@router.put("/photos/reorder")
async def reorder_photos(
    req: ReorderPhotosRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPhoto).where(UserPhoto.user_id == user.id)
    )
    photos = {p.id: p for p in result.scalars().all()}
    for idx, pid in enumerate(req.photo_ids):
        if pid in photos:
            photos[pid].sort_order = idx
    return SuccessResponse(message="Photos reordered")


@router.put("/languages")
async def update_languages(
    req: UpdateLanguagesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserLanguage).where(UserLanguage.user_id == user.id))
    for lang in result.scalars().all():
        await db.delete(lang)
    for lang in req.languages:
        db.add(UserLanguage(user_id=user.id, language=lang))
    return SuccessResponse(message=f"Languages updated: {req.languages}")


@router.get("/{user_id}", response_model=UserProfileOut)
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(
            joinedload(User.photos),
            joinedload(User.languages),
        ).where(User.id == user_id)
    )
    target = result.unique().scalar_one_or_none()
    if not target:
        raise NotFoundException("User not found")
    return profile_to_out(target)
