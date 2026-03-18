from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from arq import ArqRedis

from backend.app.db.session import async_session_factory
from backend.app.models.product import Product

logger = logging.getLogger(__name__)


async def schedule_due_scrapes(ctx: dict) -> int:
    now = datetime.now(timezone.utc)
    enqueued = 0

    async with async_session_factory() as session:
        stmt = (
            select(Product.id)
            .where(
                Product.is_active.is_(True),
                Product.next_scrape_at <= now,
            )
            .order_by(Product.next_scrape_at.asc())
            .limit(100)
        )
        result = await session.execute(stmt)
        product_ids = result.scalars().all()

    if len(product_ids) > 0:
        redis = ctx.get("redis")
        if redis is None:
            logger.error("No redis connection in context")
            return 0

        pool: ArqRedis = redis

        for pid in product_ids:
            try:
                await pool.enqueue_job("scrape_product", str(pid))
                enqueued += 1
            except Exception:
                logger.exception("Failed to enqueue job for product %s", pid)

        logger.info("Enqueued %d scrape jobs", enqueued)

    return enqueued
