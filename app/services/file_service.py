import uuid
import os
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.file import File
from app.models.user import User
from app.services.storage_service import upload_file, delete_file, generate_signed_url
from app.services.quota_service import check_quota, update_quota
from app.config import settings

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "text/plain", "text/csv",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

async def upload_user_file(
    user_id: str,
    upload: UploadFile,
    db: AsyncSession,
) -> File:
    # validate type
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type '{upload.content_type}' not allowed")

    # read file
    file_data = await upload.read()
    file_size = len(file_data)

    # validate size
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB")

    # check quota
    await check_quota(user_id, file_size, db)

    # build object key
    ext = os.path.splitext(upload.filename)[1].lower() if upload.filename else ""
    stored_name = f"{uuid.uuid4()}{ext}"
    object_key = f"{user_id}/{stored_name}"

    # upload to minio
    upload_file(file_data, object_key, upload.content_type)

    # save to db
    file = File(
        user_id=user_id,
        original_name=upload.filename or stored_name,
        stored_name=stored_name,
        content_type=upload.content_type,
        size_bytes=file_size,
        extension=ext.lstrip(".") or "bin",
        bucket=settings.MINIO_BUCKET,
        object_key=object_key,
        is_processed=upload.content_type not in IMAGE_TYPES,
    )
    db.add(file)
    await db.commit()
    await db.refresh(file)

    # update quota
    await update_quota(user_id, file_size, db)

    # trigger image processing if image
    if upload.content_type in IMAGE_TYPES:
        from app.workers.image_processor import process_image
        process_image.delay(file.id, object_key, upload.content_type)

    return file

async def get_user_files(user_id: str, db: AsyncSession, skip: int = 0, limit: int = 20):
    result = await db.execute(
        select(File)
        .where(File.user_id == user_id, File.is_deleted == False)
        .order_by(File.created_at.desc())
        .offset(skip).limit(limit)
    )
    files = result.scalars().all()

    # get user quota info
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    count_result = await db.execute(
        select(func.count()).where(File.user_id == user_id, File.is_deleted == False)
    )
    total = count_result.scalar()

    return files, total, user.used_bytes if user else 0, user.quota_bytes if user else 0

async def get_signed_url(file_id: str, user_id: str, db: AsyncSession, expires: int = 3600):
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == user_id, File.is_deleted == False)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    url = generate_signed_url(file.object_key, expires)
    return url, file.original_name

async def delete_user_file(file_id: str, user_id: str, db: AsyncSession):
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == user_id, File.is_deleted == False)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # delete from minio
    delete_file(file.object_key)

    # soft delete in db
    file.is_deleted = True
    await db.commit()

    # free up quota
    await update_quota(user_id, -file.size_bytes, db)
    return {"message": "File deleted successfully"}