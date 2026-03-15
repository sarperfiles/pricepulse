from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.deps import get_current_user
from backend.app.models.price_history import PriceHistory
from backend.app.models.product import Product
from backend.app.models.user import User
from backend.app.schemas.price_history import PriceHistoryResponse, PriceStatsResponse

router = APIRouter(prefix="/api/products", tags=["price_history"])


async def _verify_product_ownership(
    pid: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Product:
    result = await db.execute(
        select(Product).where(Product.id == pid, Product.user_id == user_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@router.get("/{product_id}/prices", response_model=list[PriceHistoryResponse])
async def list_price_history(
    product_id: uuid.UUID,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PriceHistory]:
    await _verify_product_ownership(product_id, current_user.id, db)

    query = (
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.scraped_at.desc())
    )

    if start_date is not None:
        query = query.where(PriceHistory.scraped_at >= start_date)
    if end_date is not None:
        query = query.where(PriceHistory.scraped_at <= end_date)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{product_id}/prices/stats", response_model=PriceStatsResponse)
async def get_price_stats(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PriceStatsResponse:
    product = await _verify_product_ownership(product_id, current_user.id, db)

    query = select(
        func.min(PriceHistory.price).label("min_price"),
        func.max(PriceHistory.price).label("max_price"),
        func.avg(PriceHistory.price).label("avg_price"),
        func.count(PriceHistory.id).label("total_records"),
    ).where(
        PriceHistory.product_id == product_id,
        PriceHistory.status == "success",
    )

    result = await db.execute(query)
    row = result.one()

    avg = round(row.avg_price, 2) if row.avg_price is not None else None

    return PriceStatsResponse(
        min_price=row.min_price,
        max_price=row.max_price,
        avg_price=avg,
        current_price=product.current_price,
        total_records=row.total_records,
    )
