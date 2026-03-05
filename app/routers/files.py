from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import verify_token
from app.services.file_service import (
    upload_user_file, get_user_files,
    get_signed_url, delete_user_file
)
from app.schemas.file import FileResponse, FileListResponse, SignedUrlResponse, QuotaResponse

router = APIRouter(prefix="/api/v1/files", tags=["files"])
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload["sub"]

@router.post("/upload", response_model=FileResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await upload_user_file(user_id, file, db)

@router.get("/", response_model=FileListResponse)
async def list_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    files, total, used, quota = await get_user_files(user_id, db, skip, limit)
    return FileListResponse(
        files=files,
        total=total,
        used_bytes=used,
        quota_bytes=quota,
    )

@router.get("/{file_id}/url", response_model=SignedUrlResponse)
async def get_file_url(
    file_id: str,
    expires: int = Query(3600, ge=60, le=86400),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    url, filename = await get_signed_url(file_id, user_id, db, expires)
    return SignedUrlResponse(url=url, expires_in=expires, filename=filename)

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await delete_user_file(file_id, user_id, db)

@router.get("/quota/me", response_model=QuotaResponse)
async def get_quota(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return QuotaResponse(
        used_bytes=user.used_bytes,
        quota_bytes=user.quota_bytes,
        used_gb=round(user.used_bytes / (1024**3), 3),
        quota_gb=round(user.quota_bytes / (1024**3), 2),
        percent_used=round((user.used_bytes / user.quota_bytes) * 100, 2),
    )

from app.core.security import hash_password, verify_password
from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str

@router.post("/auth/register", status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.user import User
    import uuid

    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    return {"id": user.id, "email": user.email, "username": user.username}

@router.post("/auth/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.user import User
    from app.core.security import create_access_token

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}