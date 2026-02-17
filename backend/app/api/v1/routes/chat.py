from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from typing import List

from app.core.user_settings import get_current_user, get_db
from app.models.chat import Chat, ChatMembers, Message
from app.models.user import User
from app.models.session import Session
from app.schemas.chat import (
    ChatType,
    ChatOut,
    ChatMembersRole,
    Message as MessageSchema,
    MessageStatus,
)

import traceback

router = APIRouter()


@router.post("/chats/private/{recipient_id}", response_model=ChatOut)
async def create_private_chat(
    recipient_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        recipient = await db.get(User, recipient_id)
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")

        is_self = current_user.user_id == recipient_id
        target_count = 1 if is_self else 2

        statement = (
            select(Chat)
            .join(ChatMembers)
            .where(Chat.type == ChatType.private)
            .where(ChatMembers.user_id.in_([current_user.user_id, recipient_id]))
            .group_by(Chat.chat_id)
            .having(func.count(ChatMembers.user_id) == target_count)
        )

        result = await db.execute(statement)
        existing_chat = result.scalar_one_or_none()

        if existing_chat:
            return existing_chat

        new_chat = Chat(type=ChatType.private)
        db.add(new_chat)
        await db.flush()

        members = [
            ChatMembers(
                chat_id=new_chat.chat_id,
                user_id=current_user.user_id,
                role=ChatMembersRole.member,
            )
        ]
        if not is_self:
            members.append(
                ChatMembers(
                    chat_id=new_chat.chat_id,
                    user_id=recipient_id,
                    role=ChatMembersRole.member,
                )
            )

        db.add_all(members)

        try:
            await db.commit()
            await db.refresh(new_chat)
        except Exception:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create chat.",
            )

        return new_chat

    except Exception as e:
        await db.rollback()
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}/messages", response_model=List[MessageSchema])
async def get_messages(
    chat_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify user is in the chat
    member_check = await db.execute(
        select(ChatMembers).where(
            ChatMembers.chat_id == chat_id, ChatMembers.user_id == current_user.user_id
        )
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this chat")

    # Fetch messages joined with user for usernames
    statement = (
        select(Message, User.display_username)
        .join(User, Message.sender_id == User.user_id)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(statement)

    return [
        {
            "message_id": str(msg.message_id),
            "chat_id": str(msg.chat_id),
            "sender_id": str(msg.sender_id),
            "sender_username": uname,
            "sender_device_id": str(msg.sender_device_id),
            "payload": msg.payload,
            "created_at": msg.created_at,
            "updated_at": msg.updated_at,
            "status": msg.status,
            "receiver_id": None,
            "receiver_device_id": None,
            "receiver_username": None,
        }
        for msg, uname in result.all()
    ]


@router.post("/chats/{chat_id}/messages", response_model=MessageSchema)
async def send_message(
    chat_id: uuid.UUID,
    payload: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Verify membership
        member_check = await db.execute(
            select(ChatMembers).where(
                ChatMembers.chat_id == chat_id,
                ChatMembers.user_id == current_user.user_id,
            )
        )
        if not member_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not a member of this chat")

        # Get session for device ID
        session_result = await db.execute(
            select(Session).where(Session.user_id == current_user.user_id).limit(1)
        )
        user_session = session_result.scalar_one_or_none()
        if not user_session:
            raise HTTPException(status_code=400, detail="No active session found.")

        new_message = Message(
            chat_id=chat_id,
            sender_id=current_user.user_id,
            sender_device_id=user_session.id,
            payload=payload,
            created_at=datetime.now(timezone.utc),
            status=MessageStatus.sent,
        )

        db.add(new_message)
        await db.commit()
        await db.refresh(new_message)

        return {
            "message_id": str(new_message.message_id),
            "chat_id": str(new_message.chat_id),
            "sender_id": str(new_message.sender_id),
            "sender_username": current_user.display_username,
            "sender_device_id": str(new_message.sender_device_id),
            "payload": new_message.payload,
            "created_at": new_message.created_at,
            "updated_at": None,
            "status": new_message.status,
            "receiver_id": None,
            "receiver_device_id": None,
            "receiver_username": None,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats", response_model=List[ChatOut])
async def get_chats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    statement = (
        select(Chat)
        .join(ChatMembers)
        .where(ChatMembers.user_id == current_user.user_id)
    )
    result = await db.execute(statement)
    chats = result.scalars().all()
    return chats
