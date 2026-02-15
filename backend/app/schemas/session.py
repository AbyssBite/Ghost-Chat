from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class SessionRead(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    is_active: bool
    device_info: str | None = None
    ip_address: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def coerce_uuids(cls, data: object) -> object:
        if hasattr(data, "id") and hasattr(data, "user_id"):
            return {
                "id": str(data.id) if isinstance(getattr(data, "id"), UUID) else getattr(data, "id"),
                "user_id": str(data.user_id) if isinstance(getattr(data, "user_id"), UUID) else getattr(data, "user_id"),
                "created_at": getattr(data, "created_at", None),
                "expires_at": getattr(data, "expires_at", None),
                "is_active": getattr(data, "is_active", None),
                "device_info": getattr(data, "device_info", None),
                "ip_address": getattr(data, "ip_address", None),
            }
        return data
