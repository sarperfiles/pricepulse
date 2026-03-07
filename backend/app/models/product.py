from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Interval,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.price_history import PriceHistory
    from backend.app.models.alert_rule import AlertRule
    from backend.app.models.notification import Notification
    from backend.app.models.scrape_job import ScrapeJob


class Product(BaseMixin, Base):
    __tablename__ = "products"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    custom_selector: Mapped[str | None] = mapped_column(Text, nullable=True)
    scrape_interval = mapped_column(
        Interval, server_default=text("interval '6 hours'"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    current_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")
    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_scrape_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship("User", back_populates="products")
    price_history: Mapped[list[PriceHistory]] = relationship(
        "PriceHistory", back_populates="product", lazy="selectin"
    )
    alert_rules: Mapped[list[AlertRule]] = relationship(
        "AlertRule", back_populates="product", lazy="selectin"
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification", back_populates="product", lazy="selectin"
    )
    scrape_jobs: Mapped[list[ScrapeJob]] = relationship(
        "ScrapeJob", back_populates="product", lazy="selectin"
    )
