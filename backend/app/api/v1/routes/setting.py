from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status, Form
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.core.security import hash_password, verify_password
from app.core.user_settings import get_current_user
from app.models.user import User
from app.models.session import Session
from app.models.settings import UserSettings
from app.schemas.user import UserDelete, UserUpdate, UserRead, normalize_username
from app.schemas.settings import SettingsRead, SettingsUpdate
from app.api.v1.routes.auth import CurrentAuth

router = APIRouter()


@router.get("/max-sessions")
async def get_max_sessions(
    auth: CurrentAuth = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    current_user, _ = auth

    statement = select(UserSettings).where(UserSettings.user_id == current_user.user_id)
    result = await db.execute(statement=statement)
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(
            user_id=current_user.user_id, max_sessions=2, notifications_enabled=True
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return SettingsRead.model_validate(settings)


@router.get("/settings", response_model=SettingsRead)
async def get_user_settings(
    auth: Annotated[CurrentAuth, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, _ = auth

    statement = select(UserSettings).where(UserSettings.user_id == current_user.user_id)
    result = await db.execute(statement)
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(
            user_id=current_user.user_id,
            max_sessions=2,
            notifications_enabled=True,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return SettingsRead.model_validate(settings)


@router.put("/settings/profile", response_model=UserRead)
async def update_profile(
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


@router.patch("/settings", response_model=SettingsRead)
async def update_user_settings(
    update_data: Annotated[SettingsUpdate, Form()],
    auth: Annotated[CurrentAuth, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, _ = auth

    statement = select(UserSettings).where(UserSettings.user_id == current_user.user_id)
    result = await db.execute(statement)
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(
            user_id=current_user.user_id, max_sessions=2, notifications_enabled=True
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    if update_data.max_sessions is not None:
        settings.max_sessions = max(1, min(update_data.max_sessions, 10))

    if update_data.notifications_enabled is not None:
        settings.notifications_enabled = update_data.notifications_enabled

    await db.commit()
    await db.refresh(settings)

    return SettingsRead.model_validate(settings)


@router.delete("/settings/account-delete")
async def account_delete(
    delete_data: Annotated[UserDelete, Form()],
    auth: Annotated[CurrentAuth, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, _ = auth
    if not verify_password(
        delete_data.password.get_secret_value(), current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Password incorrect"
        )
    await db.execute(delete(Session).where(Session.user_id == current_user.user_id))
    await db.execute(delete(User).where(User.user_id == current_user.user_id))

    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
