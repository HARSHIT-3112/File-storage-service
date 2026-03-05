from pydantic import BaseModel
from datetime import datetime

class FileResponse(BaseModel):
    id: str
    original_name: str
    content_type: str
    size_bytes: int
    extension: str
    is_processed: bool
    variants: dict
    created_at: datetime

    model_config = {"from_attributes": True}

class FileListResponse(BaseModel):
    files: list[FileResponse]
    total: int
    used_bytes: int
    quota_bytes: int

class SignedUrlResponse(BaseModel):
    url: str
    expires_in: int
    filename: str

class QuotaResponse(BaseModel):
    used_bytes: int
    quota_bytes: int
    used_gb: float
    quota_gb: float
    percent_used: float