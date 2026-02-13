from ..db.base import Base

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4

class UserModel(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False, autoincrement=True
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