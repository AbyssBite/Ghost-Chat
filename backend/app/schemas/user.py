from pydantic import BaseModel, SecretStr, Field, model_validator


class PublicUser(BaseModel):
    user_id: int
    username: str

    class Config:
        from_attributes = True


class UserSignup(BaseModel):
    username: str = Field(..., min_length=4, max_length=50)
    password: SecretStr = Field(..., min_length=8, max_length=255)
    repeat_password: SecretStr = Field(..., min_length=8, max_length=255)

    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserSignup":
        if self.password.get_secret_value() != self.repeat_password.get_secret_value():
            raise ValueError("Passwords do not match")
        return self


class UserLogin(BaseModel):
    username: str
    password: str


class UserLogout(BaseModel):
    session_id: str


class UserUpdate(BaseModel):
    password: str
    new_username: str | None = None
    new_password: str | None = None


class UserDelete(BaseModel):
    username: str
    password: str
