from uuid import uuid4
from typing import Annotated
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token,
    oauth2_scheme,
)
from app.core.config import settings
from app.models.user import User
from app.schemas.user import (
    UserSignin,
    UserSignup,
    PublicUser,
    UserUpdate,
    UserRead,
    UserOut,
    normalize_username,
)
from app.schemas.token import Token


router = APIRouter()


@router.post("/signup", response_model=PublicUser, status_code=status.HTTP_201_CREATED)
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

@router.post("/signin", response_model=Token, status_code=status.HTTP_200_OK)
async def signin(
    user: Annotated[UserSignin, Form()], db: AsyncSession = Depends(get_db)
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

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(exists.user_id)},
        expires_delta=access_token_expires,
    )

    return Token(access_token=access_token, token_type="bearer")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    payload = verify_access_token(token)
    if payload is None or not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # user_id = UUID(payload)

    user = await db.get(User, payload)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # return UserRead(
    #     user_id=str(user.user_id),
    #     display_username=user.display_username,
    # )
    return user


@router.get("/me", response_model=UserRead)
async def me_endpoint(current_user: Annotated[User, Depends(get_current_user)]):
    return UserRead.model_validate(current_user)


@router.put("/me", response_model=UserRead)
async def update_current_user(
    update_data: Annotated[UserUpdate, Form()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if update_data.new_username is not None:
        normalized_new = normalize_username(update_data.new_username)

        if normalized_new != current_user.normalized_username:
            statement = select(User).where(User.normalized_username == normalized_new)
            result = await db.execute(statement)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )

            current_user.display_username = (
                update_data.new_username
            )  # preserve user case
            current_user.normalized_username = (
                normalized_new  # lowercase for uniqueness
            )

    if update_data.new_password is not None:
        assert update_data.current_password is not None

        if not verify_password(
            update_data.current_password.get_secret_value(),
            current_user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        current_user.password_hash = hash_password(
            update_data.new_password.get_secret_value()
        )

    try:
        await db.commit()
        await db.refresh(current_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    return UserRead.model_validate(current_user)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    user: Annotated[UserOut, Depends(get_current_user)],
    token: Annotated[str, Depends(oauth2_scheme)],
):
    pass