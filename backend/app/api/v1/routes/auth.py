from typing import Annotated
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.core.config import settings
from app.core.user_settings import _client_ip, _device_info
from app.models.user import User
from app.models.session import Session
from app.schemas.user import (
    UserSignin,
    UserSignup,
    PublicUser,
)
from app.schemas.token import Token

CurrentAuth = tuple[User, Session]

router = APIRouter()


@router.post("/sign-up", response_model=PublicUser, status_code=status.HTTP_201_CREATED)
async def signup(
    user_in: Annotated[UserSignup, Form()], db: AsyncSession = Depends(get_db)
):
    statement = select(User).where(
        User.normalized_username == user_in.normalized_username
    )
    result = await db.execute(statement)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    if (
        user_in.password.get_secret_value()
        != user_in.repeat_password.get_secret_value()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
        )

    hashed_pwd = hash_password(user_in.password.get_secret_value())

    new_user = User(
        normalized_username=user_in.normalized_username,
        display_username=user_in.display_username,
        password_hash=hashed_pwd,
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

    return PublicUser.model_validate(new_user)


@router.post("/sign-in", response_model=Token, status_code=status.HTTP_200_OK)
async def signin(
    request: Request,
    user: Annotated[UserSignin, Form()],
    db: AsyncSession = Depends(get_db),
):
    statement = select(User).where((User.normalized_username == user.username))
    result = await db.execute(statement=statement)
    exists = result.scalar_one_or_none()

    if not exists or not verify_password(
        user.password.get_secret_value(), exists.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credentials are either wrong or non-existent",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_session = Session(
        user_id=exists.user_id,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.session_expire_days),
        is_active=True,
        device_info=_device_info(request),
        ip_address=_client_ip(request),
    )

    db.add(new_session)

    try:
        await db.commit()
        await db.refresh(new_session)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session, please try again",
        ) from e

    access_token_expires = timedelta(days=settings.session_expire_days)
    access_token = create_access_token(
        data={"sub": str(exists.user_id), "sid": str(new_session.id)},
        expires_delta=access_token_expires,
    )

    return Token(access_token=access_token, token_type="bearer")