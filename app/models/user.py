import uuid
from sqlalchemy import String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # storage quota in bytes (default 5GB)
    quota_bytes: Mapped[int] = mapped_column(BigInteger, default=5 * 1024 * 1024 * 1024)
    used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    files: Mapped[list["File"]] = relationship("File", back_populates="owner", lazy="select")