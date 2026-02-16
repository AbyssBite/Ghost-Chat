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
from app.core.config import settings as sttg
from app.core.user_settings import _client_ip, _device_info
from app.models.user import User
from app.models.session import Session
from app.schemas.user import (
    PublicUser,
    UserSignin,
    UserSignup,
)
from app.schemas.token import Token
from app.models.settings import UserSettings

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
    statement = select(User).where(User.normalized_username == user.username)
    result = await db.execute(statement)
    exists = result.scalar_one_or_none()

    if not exists or not verify_password(
        user.password.get_secret_value(), exists.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credentials are either wrong or non-existent",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt_settings = select(UserSettings).where(UserSettings.user_id == exists.user_id)
    res_settings = await db.execute(stmt_settings)
    settings = res_settings.scalar_one_or_none()
    max_sessions = settings.max_sessions if settings else 5

    stmt_sessions = (
        select(Session)
        .where(
            Session.user_id == exists.user_id,
            Session.is_active.is_(True),
        )
        .order_by(Session.created_at.asc())
    )
    res_sessions = await db.execute(stmt_sessions)
    active_sessions = res_sessions.scalars().all()

    if len(active_sessions) >= max_sessions:
        # Terminate oldest session
        oldest_session = active_sessions[0]
        oldest_session.is_active = False
        await db.commit()

    new_session = Session(
        user_id=exists.user_id,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=sttg.session_expire_days),
        is_active=True,
        device_info=_device_info(request),
        ip_address=_client_ip(request),
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    access_token = create_access_token(
        data={"sub": str(exists.user_id), "sid": str(new_session.id)},
        expires_delta=timedelta(days=sttg.session_expire_days),
    )

    return Token(access_token=access_token, token_type="bearer")
