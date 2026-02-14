from pydantic import (
    BaseModel,
    SecretStr,
    Field,
    model_validator,
    field_validator,
    ConfigDict,
    BeforeValidator,
    StringConstraints,
)
from typing import Annotated
from app.models.user import User
from uuid import UUID
from typing import Optional


def normalize_username(v: str) -> str:
    return v.lower().strip()


NormalizedUsername = Annotated[
    str,
    BeforeValidator(normalize_username),
    StringConstraints(min_length=4, max_length=50),
]


# class PublicUser(BaseModel):
#     user_id: str
#     username: str

#     model_config = ConfigDict(from_attributes=True)

#     @classmethod
#     def from_orm(cls, obj: User):
#         return cls(
#             user_id=str(obj.user_id),
#             username=obj.display_username,
#         )


class PublicUser(BaseModel):
    user_id: str
    username: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, obj: User):
        return cls(
            user_id=str(obj.user_id),
            username=obj.display_username,
        )


# class UserSignup(BaseModel):
#     display_username: str = Field(..., min_length=4, max_length=50)
#     password: SecretStr = Field(..., min_length=8, max_length=255)
#     repeat_password: SecretStr = Field(..., min_length=8, max_length=255)

#     model_config = ConfigDict(from_attributes=True)

#     @property
#     def username(self) -> str:
#         return normalize_username(self.display_username)

#     @model_validator(mode="after")
#     def check_passwords_match(self) -> "UserSignup":
#         if self.password.get_secret_value() != self.repeat_password.get_secret_value():
#             raise ValueError("Passwords do not match")
#         return self


class UserSignup(BaseModel):
    display_username: str = Field(..., min_length=4, max_length=50)
    password: SecretStr = Field(..., min_length=8, max_length=255)
    repeat_password: SecretStr = Field(..., min_length=8, max_length=255)

    model_config = ConfigDict(from_attributes=True)

    @property
    def normalized_username(self) -> str:
        return normalize_username(self.display_username)

    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserSignup":
        if self.password.get_secret_value() != self.repeat_password.get_secret_value():
            raise ValueError("Passwords do not match")
        return self


class UserSignin(BaseModel):
    username: NormalizedUsername
    password: SecretStr


class UserUpdate(BaseModel):
    current_password: Optional[SecretStr] = None
    new_username: Optional[str] = Field(None, min_length=4, max_length=50)
    new_password: Optional[SecretStr] = Field(None, min_length=8, max_length=255)
    repeat_new_password: Optional[SecretStr] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "current_password",
        "new_username",
        "new_password",
        "repeat_new_password",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

    @model_validator(mode="after")
    def validate_update(self) -> "UserUpdate":
        if self.new_username is None and self.new_password is None:
            raise ValueError("At least one field must be provided for update")

        if self.new_password is not None or self.repeat_new_password is not None:
            if self.new_password is None or self.repeat_new_password is None:
                raise ValueError(
                    "Both new_password and repeat_new_password are required"
                )
            if (
                self.new_password.get_secret_value()
                != self.repeat_new_password.get_secret_value()
            ):
                raise ValueError("New passwords do not match")
            if self.current_password is None:
                raise ValueError("current_password is required when changing password")

        return self

# class UserRead(BaseModel):
#     user_id: str
#     display_username: str

#     model_config = ConfigDict(from_attributes=True)

#     @model_validator(mode="before")
#     def convert_uuid(cls, obj):
#         return {
#             "user_id": str(obj.user_id)
#             if isinstance(obj.user_id, UUID)
#             else obj.user_id,
#             "display_username": getattr(obj, "display_username", None),
#         }


class UserRead(BaseModel):
    user_id: str
    display_username: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("user_id", mode="before")
    @classmethod
    def serialize_uuid(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

class UserOut(BaseModel):
    id: int
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class UserDelete(BaseModel):
    username: NormalizedUsername
    password: SecretStr
