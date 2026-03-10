from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl


class ProductCreate(BaseModel):
    url: HttpUrl
    name: str | None = Field(default=None, max_length=255)
    platform: str | None = Field(default=None, max_length=50)
    custom_selector: str | None = None
    scrape_interval: str | None = Field(default='6h')


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    custom_selector: str | None = None
    scrape_interval: str | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    url: str
    name: str
    platform: str | None
    custom_selector: str | None
    scrape_interval: str | None = None
    is_active: bool
    current_price: Decimal | None
    currency: str
    last_scraped_at: datetime | None
    next_scrape_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    count: int
