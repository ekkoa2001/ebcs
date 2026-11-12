from sqlalchemy import Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(Text, primary_key=True)
    salt: Mapped[bytes] = mapped_column(LargeBinary, default=b"")
    password_hash: Mapped[bytes] = mapped_column(LargeBinary)
    role: Mapped[str] = mapped_column(Text)
    active: Mapped[int] = mapped_column(Integer, default=1)


class Profile(Base):
    __tablename__ = "profiles"

    username: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, default="")
    avatar: Mapped[str] = mapped_column(Text, default="")
    team: Mapped[str] = mapped_column(Text, default="市场部")
    tag: Mapped[str] = mapped_column(Text, default="")
    joined: Mapped[str] = mapped_column(Text)
    must_change: Mapped[int] = mapped_column(Integer, default=0)
    read_cursor: Mapped[int] = mapped_column(Integer, default=0)
