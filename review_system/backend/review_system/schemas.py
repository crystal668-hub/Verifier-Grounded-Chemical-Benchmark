from typing import Any, Literal
from pydantic import BaseModel, Field
from .config import PASSWORD_MIN_LENGTH

class LoginIn(BaseModel): username: str; password: str
class RegisterIn(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH)
class UserIn(BaseModel): username: str = Field(min_length=1, max_length=120); password: str = Field(min_length=PASSWORD_MIN_LENGTH); role: Literal["developer","collaborator"] = "collaborator"
class PasswordChangeIn(BaseModel): current_password: str; new_password: str = Field(min_length=PASSWORD_MIN_LENGTH)
class PasswordResetIn(BaseModel): new_password: str = Field(min_length=PASSWORD_MIN_LENGTH)
class UserUpdateIn(BaseModel): active: bool | None = None; role: Literal["developer","collaborator"] | None = None
class CommentIn(BaseModel): body: str = Field(min_length=1, max_length=10000); parent_id: int | None = None
class DraftIn(BaseModel): track: str; title: str = "未命名题目"; payload: dict[str, Any] = Field(default_factory=dict)
class DecisionIn(BaseModel): status: Literal["needs_changes","approved","rejected"]; note: str | None = None
