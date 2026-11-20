from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

RoleName = Literal["ADMIN", "USER"]


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
    password: SecretStr = Field(min_length=1, max_length=256)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.lower()


class AuthUser(BaseModel):
    user_id: int
    username: str
    display_name: str
    email: str | None
    roles: list[RoleName]
    must_change_password: bool


class AuthLoginResponse(BaseModel):
    user: AuthUser


class PasswordChangeRequest(BaseModel):
    current_password: SecretStr
    new_password: SecretStr = Field(min_length=14, max_length=256)
    confirm_password: SecretStr

    @model_validator(mode="after")
    def verify_confirmation(self) -> "PasswordChangeRequest":
        if self.new_password.get_secret_value() != self.confirm_password.get_secret_value():
            raise ValueError("Password confirmation does not match.")
        return self


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    roles: list[RoleName] = Field(min_length=1)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.lower()

    @field_validator("roles")
    @classmethod
    def require_unique_roles(cls, value: list[RoleName]) -> list[RoleName]:
        if len(set(value)) != len(value):
            raise ValueError("Roles must be unique.")
        return value


class AdminUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    is_active: bool | None = None
    roles: list[RoleName] | None = Field(default=None, min_length=1)

    @field_validator("roles")
    @classmethod
    def require_unique_roles(cls, value: list[RoleName] | None) -> list[RoleName] | None:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("Roles must be unique.")
        return value


class AdminUserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    display_name: str
    email: str | None
    is_active: bool
    must_change_password: bool
    roles: list[RoleName]
    created_at: datetime
    last_login_at: datetime | None


class AdminUserList(BaseModel):
    total: int
    items: list[AdminUserView]


class TemporaryPasswordResponse(BaseModel):
    user: AdminUserView
    temporary_password: str


class LoginAttemptView(BaseModel):
    login_attempt_id: int
    username: str
    remote_address: str | None
    succeeded: bool
    attempted_at: datetime


class AuditLogView(BaseModel):
    audit_log_id: int
    actor_username: str | None
    action: str
    entity_type: str
    entity_id: str | None
    outcome: str
    details: dict[str, object]
    remote_address: str | None
    created_at: datetime
