from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.user import User

async def check_quota(user_id: str, file_size: int, db: AsyncSession):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.used_bytes + file_size > user.quota_bytes:
        used_gb = round(user.used_bytes / (1024**3), 2)
        quota_gb = round(user.quota_bytes / (1024**3), 2)
        raise HTTPException(
            status_code=400,
            detail=f"Storage quota exceeded. Used: {used_gb}GB / {quota_gb}GB"
        )
    return user

async def update_quota(user_id: str, size_delta: int, db: AsyncSession):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.used_bytes = max(0, user.used_bytes + size_delta)
        await db.commit()