from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class AlertRuleCreate(BaseModel):
    rule_type: str
    target_price: Decimal | None = None
    pct_threshold: Decimal | None = None


class AlertRuleUpdate(BaseModel):
    target_price: Decimal | None = None
    pct_threshold: Decimal | None = None
    is_active: bool | None = None


class AlertRuleResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    user_id: uuid.UUID
    rule_type: str
    target_price: Decimal | None
    pct_threshold: Decimal | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
