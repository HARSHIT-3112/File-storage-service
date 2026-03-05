from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str

    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "file-storage"
    MINIO_SECURE: bool = False

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    MAX_FILE_SIZE_MB: int = 50
    DEFAULT_QUOTA_GB: int = 5

    APP_NAME: str = "FileStorageService"
    DEBUG: bool = False

    class Config:
        env_file = ".env"

settings = Settings()