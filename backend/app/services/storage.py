from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import settings

CONTENT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _cloudinary_configured() -> bool:
    return bool(
        settings.cloudinary_cloud_name
        and settings.cloudinary_api_key
        and settings.cloudinary_api_secret
        and "YOUR_" not in settings.cloudinary_cloud_name
    )


async def save_image(file: UploadFile) -> str:
    suffix = CONTENT_TYPES.get(file.content_type, Path(file.filename or "").suffix or ".jpg")
    data = await file.read()
    if _cloudinary_configured():
        import cloudinary
        import cloudinary.uploader

        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
        )
        result = cloudinary.uploader.upload(data, folder="fashion-forecast")
        return result["secure_url"]

    folder = Path(settings.upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid4().hex}{suffix}"
    path = folder / name
    path.write_bytes(data)
    return f"/uploads/{name}"
