from pydantic import BaseModel, Field


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


class PasswordInput(BaseModel):
    current: str = Field(max_length=200)
    password: str = Field(min_length=12, max_length=200)


class UserCreateInput(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=12, max_length=200)
    role: str
    active: bool = True


class UserUpdateInput(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(default="", max_length=200)
    role: str
    active: bool


class TeamUpdateInput(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    team: str = Field(default="", max_length=80)
    tag: str = Field(default="", max_length=80)


class ProfileUpdateInput(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    avatar: str = Field(default="", max_length=450000)
