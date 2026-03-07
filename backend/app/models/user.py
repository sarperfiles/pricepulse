from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from backend.app.models.alert_rule import AlertRule
    from backend.app.models.product import Product
    from backend.app.models.notification import Notification


class User(BaseMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    api_key: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )

    products: Mapped[list[Product]] = relationship(
        "Product", back_populates="user", lazy="selectin"
    )
    alert_rules: Mapped[list[AlertRule]] = relationship(
        "AlertRule", back_populates="user", lazy="selectin"
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification", back_populates="user", lazy="selectin"
    )
