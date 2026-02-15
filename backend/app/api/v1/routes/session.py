from uuid import UUID
from typing import Annotated, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status, HTTPException, Path, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.session import get_db
from app.models.session import Session
from app.schemas.session import SessionRead
from app.api.v1.routes.auth import get_current_user, CurrentAuth

router = APIRouter()


@router.get("/active-sessions", response_model=List[SessionRead])
async def list_active_sessions(
    auth: Annotated[CurrentAuth, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
):
    response.headers["Cache-Control"] = "no-store"
    current_user, _ = auth

    now_utc = datetime.now(timezone.utc)
    statement = select(Session).where(
        and_(
            Session.user_id == current_user.user_id,
            Session.is_active.is_(True),
            Session.expires_at > now_utc,
        )
    )
    result = await db.execute(statement=statement)
    sessions = result.scalars().all()

    return [SessionRead.model_validate(s) for s in sessions]


@router.delete(
    "/terminate-session/{session_id}",
    response_model=SessionRead,
    status_code=status.HTTP_200_OK,
)
async def terminate_session(
    auth: Annotated[CurrentAuth, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    session_id: UUID = Path(..., description="ID of the session to terminate"),
):
    current_user, _ = auth

    statement = select(Session).where(
        Session.id == session_id,
        Session.user_id == current_user.user_id,
        Session.is_active.is_(True),
    )
    result = await db.execute(statement=statement)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already terminated",
        )

    session.is_active = False
    await db.commit()
    await db.refresh(session)

    return SessionRead.model_validate(session)
