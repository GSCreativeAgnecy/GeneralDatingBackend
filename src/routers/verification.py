from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.auth_deps import get_current_user
from core.security import generate_otp, store_otp_async, verify_otp_async
from core.exceptions import ValidationException
from core.uploads import save_image_upload
from schemas import VerificationStatusOut, SuccessResponse

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/verification", tags=["verification"])


@router.get("/status", response_model=VerificationStatusOut)
async def verification_status(user=Depends(get_current_user)):
    return VerificationStatusOut(
        phone_verified=user.phone_verified,
        photo_verified=user.photo_verified,
    )


@router.post("/phone/send-otp")
async def send_phone_verification_otp(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    otp = generate_otp()
    await store_otp_async(user.phone_number, otp, db)
    return {"success": True, "expires_in_seconds": settings.OTP_EXPIRE_SECONDS, "otp": otp}


@router.post("/phone/verify")
async def verify_phone(otp: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if await verify_otp_async(user.phone_number, otp, db):
        user.phone_verified = True
        return SuccessResponse(message="Phone verified")
    raise ValidationException("Invalid OTP")


@router.post("/photo")
async def submit_photo_verification(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    await save_image_upload(file, user.id, subdir="verification")
    user.photo_verified = True
    return SuccessResponse(message="Photo verification submitted")
