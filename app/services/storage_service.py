import uuid
from minio import Minio
from minio.error import S3Error
from datetime import timedelta
from app.config import settings

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)

def ensure_bucket():
    if not minio_client.bucket_exists(settings.MINIO_BUCKET):
        minio_client.make_bucket(settings.MINIO_BUCKET)

def upload_file(file_data: bytes, object_key: str, content_type: str) -> str:
    import io
    ensure_bucket()
    minio_client.put_object(
        settings.MINIO_BUCKET,
        object_key,
        io.BytesIO(file_data),
        length=len(file_data),
        content_type=content_type,
    )
    return object_key

def delete_file(object_key: str):
    try:
        minio_client.remove_object(settings.MINIO_BUCKET, object_key)
    except S3Error:
        pass

def generate_signed_url(object_key: str, expires_seconds: int = 3600) -> str:
    url = minio_client.presigned_get_object(
        settings.MINIO_BUCKET,
        object_key,
        expires=timedelta(seconds=expires_seconds),
    )
    return url