from ..db.base import Base

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class UserModel(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False, autoincrement=True
    )
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
