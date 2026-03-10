from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    product_id: uuid.UUID
    alert_rule_id: uuid.UUID | None
    title: str
    message: str
    is_read: bool
    old_price: Decimal | None
    new_price: Decimal | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
    total: int
