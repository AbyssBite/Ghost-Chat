from pydantic import (
    BaseModel,
    SecretStr,
    Field,
    model_validator,
    ConfigDict,
    BeforeValidator,
    StringConstraints,
)
from typing import Annotated
from app.models.user import User


def normalize_username(v: str) -> str:
    return v.lower().strip()


NormalizedUsername = Annotated[
    str,
    BeforeValidator(normalize_username),
    StringConstraints(min_length=4, max_length=50),
]


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


class UserSignup(BaseModel):
    display_username: str = Field(..., min_length=4, max_length=50)
    password: SecretStr = Field(..., min_length=8, max_length=255)
    repeat_password: SecretStr = Field(..., min_length=8, max_length=255)
    username: NormalizedUsername = Field(..., alias="display_username")

    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserSignup":
        if self.password.get_secret_value() != self.repeat_password.get_secret_value():
            raise ValueError("Passwords do not match")
        return self


class UserSignin(BaseModel):
    username: NormalizedUsername
    password: SecretStr


class UserUpdate(BaseModel):
    current_password: SecretStr
    new_username: NormalizedUsername | None = None
    new_password: SecretStr | None = Field(None, min_length=8, max_length=255)
    repeat_new_password: SecretStr | None = None

    @model_validator(mode="after")
    def validate_password_change(self) -> "UserUpdate":
        if self.new_password is not None:
            if self.repeat_new_password is None:
                raise ValueError(
                    "repeat_new_password is required when changing password"
                )
            if (
                self.new_password.get_secret_value()
                != self.repeat_new_password.get_secret_value()
            ):
                raise ValueError("New passwords do not match")
        return self

    @model_validator(mode="after")
    def at_least_one_change(self) -> "UserUpdate":
        if self.new_username is None and self.new_password is None:
            raise ValueError("At least one field must be provided for update")
        return self


class UserOut(BaseModel):
    id: int
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class UserDelete(BaseModel):
    username: NormalizedUsername
    password: SecretStr
