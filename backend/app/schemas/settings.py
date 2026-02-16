from pydantic import BaseModel, ConfigDict, Field


class MaxSessionUpdate(BaseModel):
    max_sessions: int = Field(..., ge=1, le=10)


class SettingsRead(BaseModel):
    max_sessions: int
    notifications_enabled: bool = True

    model_config = ConfigDict(from_attributes=True)


class SettingsUpdate(BaseModel):
    max_sessions: int | None = None
    notifications_enabled: bool | None = None
