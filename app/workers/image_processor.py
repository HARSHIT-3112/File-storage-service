from celery import Celery
from PIL import Image
import io
from app.config import settings
from app.services.storage_service import minio_client, upload_file

celery_app = Celery(
    "image_processor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

VARIANTS = {
    "thumbnail": (150, 150),
    "medium": (600, 600),
    "large": (1200, 1200),
}

@celery_app.task(name="process_image")
def process_image(file_id: str, object_key: str, content_type: str):
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select
    from app.models.file import File

    # get original from minio
    response = minio_client.get_object(settings.MINIO_BUCKET, object_key)
    original_data = response.read()
    response.close()

    image = Image.open(io.BytesIO(original_data))
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    variants = {}

    for name, size in VARIANTS.items():
        img_copy = image.copy()
        img_copy.thumbnail(size, Image.LANCZOS)

        buf = io.BytesIO()
        img_copy.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        variant_data = buf.read()

        # store variant: userId/variants/fileId_thumbnail.jpg
        base_key = object_key.rsplit(".", 1)[0]
        variant_key = f"{base_key}_{name}.jpg"
        upload_file(variant_data, variant_key, "image/jpeg")
        variants[name] = variant_key

    # update db synchronously via sync engine
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url)
    Session = sessionmaker(engine)

    with Session() as session:
        file = session.execute(select(File).where(File.id == file_id)).scalar_one_or_none()
        if file:
            file.variants = variants
            file.is_processed = True
            session.commit()

    engine.dispose()
    return variants