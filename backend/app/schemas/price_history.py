from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PriceHistoryResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    price: Decimal
    currency: str
    scraped_at: datetime
    status: str

    model_config = {"from_attributes": True}


class PriceStatsResponse(BaseModel):
    min_price: Decimal | None
    max_price: Decimal | None
    avg_price: Decimal | None
    current_price: Decimal | None
    total_records: int
