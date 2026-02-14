from ..db.base import Base

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        default=lambda: str(uuid4()),
        unique=True,
        index=True,
    )
    normalized_username: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    display_username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)