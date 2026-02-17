import re
from uuid import UUID
from typing import Annotated
from datetime import datetime, timezone
from fastapi import Request, WebSocket, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import oauth2_scheme, verify_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.session import Session


async def validate_session_logic(payload: dict, db: AsyncSession):
    if not payload or not payload.get("sub") or not payload.get("sid"):
        return None

    try:
        user_id = UUID(payload.get("sub"))
        session_id = UUID(payload.get("sid"))
    except ValueError, TypeError:
        return None

    user = await db.get(User, user_id)
    session_record = await db.get(Session, session_id)

    if not user or not session_record or not session_record.is_active:
        return None

    now_utc = datetime.now(timezone.utc)
    expires_at = session_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now_utc or session_record.user_id != user_id:
        return None

    # return (user, session_record)
    return user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await validate_session_logic(payload, db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result


async def get_current_user_ws(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    auth_header = websocket.headers.get("authorization") or websocket.headers.get(
        "Authorization"
    )

    if not auth_header or not auth_header.startswith("Bearer "):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    token = auth_header.split(" ")[1]
    payload = verify_access_token(token)
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    result = await validate_session_logic(payload, db)
    if not result:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    return result


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client = forwarded.split(",")[0].strip()
        if client:
            return client
    if request.client is not None:
        return request.client.host
    return request.headers.get("x-real-ip")


def _device_info(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    if not ua or not ua.strip():
        return None
    ua = ua.strip()
    parts: list[str] = []
    browser_name = None
    browser_ver = None
    if "Chrome" in ua and "Edg" not in ua:
        m = re.search(r"Chrome/(\d+(?:\.\d+)*)", ua, re.I)
        if m:
            browser_name, browser_ver = "Chrome", m.group(1).split(".")[0]
    elif "Firefox" in ua:
        m = re.search(r"Firefox/(\d+(?:\.\d+)*)", ua, re.I)
        if m:
            browser_name, browser_ver = "Firefox", m.group(1).split(".")[0]
    elif "Safari" in ua and "Chrome" not in ua:
        m = re.search(r"Version/(\d+(?:\.\d+)*)", ua, re.I)
        browser_name = "Safari"
        browser_ver = m.group(1).split(".")[0] if m else None
    elif "Edg" in ua:
        m = re.search(r"Edg/(\d+(?:\.\d+)*)", ua, re.I)
        if m:
            browser_name, browser_ver = "Edge", m.group(1).split(".")[0]
    if browser_name:
        parts.append(f"{browser_name} {browser_ver}" if browser_ver else browser_name)
    os_name = None
    if "Android" in ua:
        m = re.search(r"Android (\d+(?:\.\d+)*)?", ua, re.I)
        os_name = f"Android {m.group(1)}" if m and m.group(1) else "Android"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iPhone" if "iPhone" in ua else "iPad"
    elif "Windows" in ua:
        os_name = "Windows"
    elif "Mac OS" in ua or "Macintosh" in ua:
        os_name = "macOS"
    elif "Linux" in ua:
        os_name = "Linux"
    if os_name:
        parts.append(os_name)
    if "Mobile" in ua:
        parts.append("Mobile")
    summary = ", ".join(parts) if parts else ua[:80] + ("..." if len(ua) > 80 else "")
    return summary
