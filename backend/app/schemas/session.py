from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionRead(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    is_active: bool
    device_info: str | None = None
    ip_address: str | None = None

    model_config = ConfigDict(from_attributes=True)
