from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import json

from app.core.user_settings import get_current_user_ws, get_db
from app.crud.chat import add_message, is_chat_member
from app.models.chat import Chat
from app.schemas.chat import Message as MessageSchema
from app.core.ws_settings import ConnectionManager

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/chat/{chat_id}")
async def chat_ws(
    websocket: WebSocket,
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    auth_result=Depends(get_current_user_ws),
):
    if auth_result is None:
        return

    user, session = auth_result

    try:
        chat_uuid = uuid.UUID(chat_id)
        chat_obj = await db.get(Chat, chat_uuid)

        if not chat_obj:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        is_member = await is_chat_member(db=db, chat_id=chat_uuid, user_id=user.id)

        if not is_member:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(chat_id, websocket)

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
                continue

            event_type = data.get("event")
            payload = data.get("payload")

            if event_type == "send_message":
                try:
                    message: MessageSchema = await add_message(
                        db=db,
                        chat_id=chat_uuid,
                        sender_id=user.id,
                        sender_device_id=session.id,
                        payload=payload,
                    )
                    await db.commit()
                    await manager.broadcast(chat_id, message.dict(), exclude=websocket)
                except Exception:
                    await websocket.send_json({"error": "Failed to save message"})

            elif event_type == "typing":
                await manager.broadcast(
                    chat_id,
                    {"event": "typing", "user_id": str(user.id)},
                    exclude=websocket,
                )
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(chat_id, websocket)
