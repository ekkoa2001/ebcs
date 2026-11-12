from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SessionRecord(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), index=True)
    csrf: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[float] = mapped_column(Float)
    active_at: Mapped[float] = mapped_column(Float, default=0)
    payload: Mapped[str] = mapped_column(Text, default="{}")


class Role(Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(32))


class Permission(Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str] = mapped_column(String(200))


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_name", "permission_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_name: Mapped[str] = mapped_column(ForeignKey("roles.name"), index=True)
    permission_code: Mapped[str] = mapped_column(ForeignKey("permissions.code"), index=True)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    time: Mapped[str] = mapped_column(String(19), index=True)
    actor: Mapped[str] = mapped_column(String(100), index=True)
    module: Mapped[str] = mapped_column(String(40), default="v1")
    action: Mapped[str] = mapped_column(String(300))
    object_type: Mapped[str] = mapped_column(String(40), default="")
    object_id: Mapped[str] = mapped_column(String(80), default="")
    result: Mapped[str] = mapped_column(String(20), default="success")
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    repeat_count: Mapped[int] = mapped_column(Integer, default=1)
