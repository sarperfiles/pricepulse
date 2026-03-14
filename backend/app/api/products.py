from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.redis import get_redis
from backend.app.db.session import get_db
from backend.app.deps import get_current_user
from backend.app.models.user import User

if TYPE_CHECKING:
    from backend.app.models.product import Product

from backend.app.schemas.product import ProductCreate, ProductListResponse, ProductResponse, ProductUpdate
from backend.app.services import product_service

router = APIRouter(prefix="/api/products", tags=["products"])


def _product_to_response(p: Product) -> dict:
    interval_str: str | None = None
    if p.scrape_interval is not None:
        hrs = int(p.scrape_interval.total_seconds()) // 3600
        interval_str = f"{hrs}h"
    return {
        "id": p.id,
        "user_id": p.user_id,
        "url": p.url,
        "name": p.name,
        "platform": p.platform,
        "custom_selector": p.custom_selector,
        "scrape_interval": interval_str,
        "is_active": p.is_active,
        "current_price": p.current_price,
        "currency": p.currency,
        "last_scraped_at": p.last_scraped_at,
        "next_scrape_at": p.next_scrape_at,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    product = await product_service.create_product(body, current_user.id, db)
    return _product_to_response(product)


@router.get("/", response_model=ProductListResponse)
async def list_products(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    products, total = await product_service.get_products(
        current_user.id, db, offset=offset, limit=limit, active_only=active_only
    )
    items = []
    for p in products:
        items.append(_product_to_response(p))
    return {
        "items": items,
        "count": total,
    }


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    product = await product_service.get_product(product_id, current_user.id, db)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return _product_to_response(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    product = await product_service.get_product(product_id, current_user.id, db)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    updated = await product_service.update_product(product, body, db)
    return _product_to_response(updated)


@router.delete("/{product_id}", response_model=ProductResponse)
async def delete_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    product = await product_service.get_product(product_id, current_user.id, db)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    deactivated = await product_service.delete_product(product, db)
    return _product_to_response(deactivated)


@router.post("/{product_id}/scrape", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scrape(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
) -> dict:
    product = await product_service.get_product(product_id, current_user.id, db)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    job = await product_service.trigger_scrape(product, db, redis_client=redis)
    return {
        "job_id": str(job.id),
        "status": job.status,
        "message": "Scrape job enqueued",
    }
