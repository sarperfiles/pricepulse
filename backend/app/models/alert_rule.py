from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.product import Product


class AlertRule(BaseMixin, Base):
    __tablename__ = "alert_rules"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    pct_threshold: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    product: Mapped[Product] = relationship("Product", back_populates="alert_rules")
    user: Mapped[User] = relationship("User", back_populates="alert_rules")
