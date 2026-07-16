import uuid
import secrets
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile

from core.config import settings

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
ALLOWED_IMAGE_MIMES = {
    "image/jpeg", "image/png", "image/webp", "image/heic", "image/heif",
}


def sanitize_filename(filename: Optional[str]) -> str:
    stem = Path(filename or "file").stem
    stem = "".join(c for c in stem if c.isalnum() or c in "._- ") or "file"
    return stem.strip().replace(" ", "_")


def get_safe_filename(prefix: str, extension: str) -> str:
    return f"{prefix}_{secrets.token_hex(16)}{extension}"


async def validate_and_save_upload(
    file: UploadFile,
    upload_subdir: str,
    *,
    max_size_bytes: int,
    allowed_extensions: set[str],
    allowed_mimes: set[str],
    filename_prefix: str = "",
) -> str:
    if not file.filename:
        from core.exceptions import ValidationException
        raise ValidationException("File must have a filename")

    ext = Path(file.filename).suffix.lower()
    if not ext:
        ext = ".jpg" if upload_subdir == "photos" else ".m4a"
    if ext not in allowed_extensions:
        from core.exceptions import ValidationException
        raise ValidationException(
            f"File type '{ext}' not allowed. Accepted: {', '.join(sorted(allowed_extensions))}"
        )

    if file.content_type and file.content_type not in allowed_mimes:
        from core.exceptions import ValidationException
        raise ValidationException(
            f"MIME type '{file.content_type}' not allowed."
        )

    safe_name = get_safe_filename(filename_prefix, ext)
    filepath = settings.UPLOAD_DIR / upload_subdir / safe_name
    filepath.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    try:
        async with aiofiles.open(filepath, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size_bytes:
                    await f.close()
                    filepath.unlink(missing_ok=True)
                    from core.exceptions import ValidationException
                    raise ValidationException(
                        f"File exceeds maximum size of {max_size_bytes // (1024 * 1024)}MB"
                    )
                await f.write(chunk)
    except Exception:
        filepath.unlink(missing_ok=True)
        raise

    url_prefix = settings.API_V1_PREFIX or "/api/v1"
    return f"{url_prefix}/uploads/{upload_subdir}/{safe_name}"


async def save_image_upload(
    file: UploadFile,
    user_id: int,
    subdir: str = "photos",
) -> str:
    return await validate_and_save_upload(
        file,
        subdir,
        max_size_bytes=settings.MAX_PHOTO_SIZE_MB * 1024 * 1024,
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
        allowed_mimes=ALLOWED_IMAGE_MIMES,
        filename_prefix=f"u{user_id}",
    )
