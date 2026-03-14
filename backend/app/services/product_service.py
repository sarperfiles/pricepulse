from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from arq import create_pool
from arq.connections import RedisSettings
from bs4 import BeautifulSoup
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.models.product import Product
from backend.app.models.scrape_job import ScrapeJob
from backend.app.schemas.product import ProductCreate, ProductUpdate

INTERVAL_MAP: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "12h": timedelta(hours=12),
    "24h": timedelta(hours=24),
}

KNOWN_PLATFORMS: list[tuple[str, str]] = [
    ("amazon", "amazon"),
    ("ebay", "ebay"),
    ("getyourguide", "getyourguide"),
    ("hepsiburada", "hepsiburada"),
]


async def fetch_page_title(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.find("title")
        if tag:
            title = tag.get_text(strip=True)
            title = re.sub(r"\s+", " ", title)
            if len(title) > 0:
                return title[:255]
    except Exception:
        pass
    # fallback to domain name
    try:
        domain = urlparse(url).netloc
        domain = re.sub(r"^www\.", "", domain)
        return domain or "Untitled Product"
    except Exception:
        return "Untitled Product"


def detect_platform(url: str) -> str | None:
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return None
    for kw, platform in KNOWN_PLATFORMS:
        if kw in domain:
            return platform
    return None


def parse_interval(interval_str: str | None) -> timedelta:
    if interval_str is None:
        return timedelta(hours=6)
    return INTERVAL_MAP.get(interval_str, timedelta(hours=6))


async def create_product(
    data: ProductCreate,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Product:
    url_str = str(data.url)
    name = data.name if data.name else await fetch_page_title(url_str)
    platform = data.platform or detect_platform(url_str)
    interval = parse_interval(data.scrape_interval)
    now = datetime.now(timezone.utc)

    product = Product(
        user_id=user_id,
        url=url_str,
        name=name,
        platform=platform,
        custom_selector=data.custom_selector,
        scrape_interval=interval,
        next_scrape_at=now,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def get_products(
    user_id: uuid.UUID,
    db: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 50,
    active_only: bool = True,
) -> tuple[list[Product], int]:
    base = select(Product).where(Product.user_id == user_id)
    if active_only:
        base = base.where(Product.is_active.is_(True))

    count_q = select(func.count()).select_from(base.subquery())
    result = await db.execute(count_q)
    total = result.scalar_one()

    items_q = base.order_by(Product.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(items_q)
    products = list(result.scalars().all())

    return products, total


async def get_product(
    product_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Product | None:
    q = select(Product).where(
        Product.id == product_id,
        Product.user_id == user_id,
    )
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def update_product(
    product: Product,
    data: ProductUpdate,
    db: AsyncSession,
) -> Product:
    update_data = data.model_dump(exclude_unset=True)

    if "scrape_interval" in update_data and update_data["scrape_interval"] is not None:
        interval = parse_interval(update_data.pop("scrape_interval"))
        product.scrape_interval = interval
        product.next_scrape_at = datetime.now(timezone.utc) + interval
    else:
        update_data.pop("scrape_interval", None)

    for field, value in update_data.items():
        setattr(product, field, value)

    await db.flush()
    await db.refresh(product)
    return product


async def delete_product(
    product: Product,
    db: AsyncSession,
) -> Product:
    product.is_active = False
    await db.flush()
    await db.refresh(product)
    return product


async def trigger_scrape(
    product: Product,
    db: AsyncSession,
    redis_client: object | None = None,
) -> ScrapeJob:
    job = ScrapeJob(
        product_id=product.id,
        status="pending",
        scraper_type=product.platform,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    if redis_client is not None:
        try:
            pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
            await pool.enqueue_job(
                "scrape_product",
                str(product.id),
                str(job.id),
            )
        except Exception:
            # TODO: proper error handling
            pass

    return job
