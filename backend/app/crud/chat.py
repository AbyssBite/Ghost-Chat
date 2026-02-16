from __future__ import annotations

from app.models.chat import Message, ChatMembers, ChatMembersRole
from app.models.user import User
from app.schemas.chat import (
    Message as MessageSchema,
    MessageStatus,
    Chat,
    ChatType,
)
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

import uuid
from datetime import datetime
from typing import cast


async def get_messages(db: AsyncSession, chat_id: uuid.UUID, limit: int):
    msg_stmt = (
        select(Message, User.display_username)
        .join(User, User.user_id == Message.sender_id)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(msg_stmt)
    messages = result.all()

    members_stmt = (
        select(User.user_id, User.display_username)
        .join(ChatMembers, ChatMembers.user_id == User.user_id)
        .where(ChatMembers.chat_id == chat_id)
    )
    members_result = await db.execute(members_stmt)
    all_members = members_result.all()

    members_dict = {str(uid): username for uid, username in all_members}

    messages_list = []
    for msg, sender_username in messages:
        receiver_usernames = [
            username
            for uid, username in members_dict.items()
            if uid != str(msg.sender_id)
        ]
        messages_list.append(
            MessageSchema(
                message_id=str(msg.message_id),
                chat_id=str(msg.chat_id),
                sender_id=str(msg.sender_id),
                sender_username=sender_username,
                sender_device_id=str(msg.sender_device_id),
                payload=msg.payload,
                created_at=msg.created_at,
                updated_at=msg.updated_at,
                status=msg.status,
                receiver_username=receiver_usernames,
            )
        )

    return messages_list


async def get_or_create_private_chat(
    db: AsyncSession,
    user1_id: uuid.UUID,
    user2_id: uuid.UUID,
) -> uuid.UUID:
    u1, u2 = sorted([user1_id, user2_id])

    stmt = (
        select(Chat)
        .join(ChatMembers, Chat.chat_id == ChatMembers.chat_id)  # type: ignore[arg-type]
        .where(Chat.type == ChatType.private)  # type: ignore[arg-type]
        .group_by(Chat.chat_id)
        .having(
            func.count(case((ChatMembers.user_id.in_([u1, u2]), 1), else_=None)) == 2
        )
        .having(func.count(ChatMembers.user_id) == 2)
    )

    result = await db.execute(stmt)
    existing_chat = result.scalar_one_or_none()

    if existing_chat is not None:
        return existing_chat.chat_id  # type: ignore[union-attr]

    new_chat = Chat(type=ChatType.private)  # type: ignore[union-attr]
    db.add(new_chat)
    await db.flush()

    chat_id = cast(uuid.UUID, new_chat.chat_id)  # type: ignore[union-attr]

    db.add_all(
        ChatMembers(
            chat_id=chat_id,
            user_id=uid,
            role=ChatMembersRole.member,
        )
        for uid in (u1, u2)
    )

    await db.commit()
    return chat_id


async def add_message(
    db: AsyncSession,
    chat_id: uuid.UUID,
    sender_id: uuid.UUID,
    sender_device_id: uuid.UUID,
    payload: str,
    updated_at: datetime | None = None,
    status: MessageStatus = MessageStatus.sent,
) -> MessageSchema:
    msg = Message(
        chat_id=chat_id,
        sender_id=sender_id,
        sender_device_id=sender_device_id,
        payload=payload,
        updated_at=updated_at,
        status=status,
    )
    db.add(msg)
    await db.flush()

    sender_result = await db.execute(
        select(User.display_username).where(User.user_id == sender_id)
    )
    sender_username = sender_result.scalar_one()

    members_result = await db.execute(
        select(User.user_id, User.display_username)
        .join(ChatMembers, ChatMembers.user_id == User.user_id)
        .where(ChatMembers.chat_id == chat_id)
    )
    all_members = members_result.all()
    receiver_usernames = [username for uid, username in all_members if uid != sender_id]
    receiver_ids = [str(uid) for uid, _ in all_members if uid != sender_id]

    message_schema = MessageSchema(
        message_id=str(msg.message_id),
        chat_id=str(chat_id),
        sender_id=str(sender_id),
        sender_username=sender_username,
        sender_device_id=str(sender_device_id),
        payload=msg.payload,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
        status=msg.status,
        receiver_username=receiver_usernames,
        receiver_id=receiver_ids,
        receiver_device_id=None,
    )

    return message_schema


async def is_chat_member(
    db: AsyncSession,
    chat_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    stmt = select(ChatMembers).where(
        ChatMembers.chat_id == chat_id,
        ChatMembers.user_id == user_id,
    )

    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    return member is not None
