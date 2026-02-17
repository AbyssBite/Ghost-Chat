import uuid
from pydantic import BaseModel, ConfigDict
from enum import Enum
from datetime import datetime
from typing import List


class ChatType(str, Enum):
    private = "private"
    group = "group"


class ChatMembersRole(str, Enum):
    admin = "admin"
    member = "member"
    guest = "guest"


class MessageStatus(str, Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"


class Chat(BaseModel):
    chat_id: str
    type: ChatType
    created_at: datetime


class ChatMember(BaseModel):
    user_id: str
    username: str
    joined_at: datetime
    role: ChatMembersRole


class ChatOut(BaseModel):
    chat_id: uuid.UUID
    type: ChatType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message_id: str
    chat_id: str
    sender_id: str
    sender_username: str
    sender_device_id: str
    payload: str
    created_at: datetime
    updated_at: datetime | None = None
    status: MessageStatus
    receiver_id: List[str] | None = None
    receiver_device_id: List[str] | None = None
    receiver_username: List[str] | None = None
