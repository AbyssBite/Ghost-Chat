from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserSignup, PublicUser
from app.core.security import hash_password

router = APIRouter()


@router.post("/signup", response_model=PublicUser, status_code=status.HTTP_201_CREATED)
async def signup(
    user_in: Annotated[UserSignup, Form()], db: AsyncSession = Depends(get_db)
):
    statement = select(User).where(User.normalized_username == user_in.username)
    result = await db.execute(statement)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    hashed_pwd = hash_password(user_in.password.get_secret_value())

    new_user = User(
        normalized_username=user_in.username,
        display_username=user_in.display_username,
        password_hash=hashed_pwd,
        session_id=str(uuid4()),
    )

    db.add(new_user)

    try:
        await db.commit()
        await db.refresh(new_user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user, please try again",
        ) from e

    return PublicUser.from_orm(new_user)
