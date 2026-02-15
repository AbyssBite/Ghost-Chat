from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.core.security import (
    hash_password,
    verify_password,
)
from app.core.user_settings import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserUpdate,
    UserRead,
    normalize_username,
)
from app.api.v1.routes.auth import CurrentAuth
from app.models.session import Session


router = APIRouter()


@router.get("/me", response_model=UserRead)
async def me_endpoint(
    auth: Annotated[CurrentAuth, Depends(get_current_user)],
):
    current_user, _ = auth
    return UserRead.model_validate(current_user)


@router.put("/me", response_model=UserRead)
async def update_current_user(
    update_data: Annotated[UserUpdate, Form()],
    auth: Annotated[CurrentAuth, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, _ = auth
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

            current_user.display_username = update_data.new_username
            current_user.normalized_username = normalized_new

    if update_data.new_password is not None:
        if update_data.current_password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to set a new password",
            )

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
    auth: Annotated[CurrentAuth, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _, current_session = auth
    await db.execute(
        update(Session).where(Session.id == current_session.id).values(is_active=False)
    )
    await db.commit()
    return None
