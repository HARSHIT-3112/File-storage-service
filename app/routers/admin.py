from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.core.security import verify_token
from app.models.user import User
from app.models.file import File

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]

@router.get("/stats")
async def get_stats(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.execute(select(func.count()).select_from(User))
    total_files = await db.execute(
        select(func.count()).where(File.is_deleted == False)
    )
    total_storage = await db.execute(
        select(func.sum(File.size_bytes)).where(File.is_deleted == False)
    )
    return {
        "total_users": total_users.scalar(),
        "total_files": total_files.scalar(),
        "total_storage_bytes": total_storage.scalar() or 0,
        "total_storage_gb": round((total_storage.scalar() or 0) / (1024**3), 3),
    }