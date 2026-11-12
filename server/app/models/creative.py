from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CreativeHook(Base):
    __tablename__ = "creative_hooks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    code: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text, default="")
    hook_type: Mapped[str] = mapped_column(String(120), default="")
    product: Mapped[str] = mapped_column(String(200), default="")
    audience: Mapped[str] = mapped_column(String(200), default="")
    scene: Mapped[str] = mapped_column(String(200), default="")
    reference_material: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="待筛选")
    is_example: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(64), default="")
    owner: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[str] = mapped_column(String(40), default="")
    updated_at: Mapped[str] = mapped_column(String(40), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    deleted_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    legacy_json: Mapped[str] = mapped_column(Text, default="")
