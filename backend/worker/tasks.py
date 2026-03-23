from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import selectinload
from sqlalchemy import select

from backend.app.db.session import async_session_factory
from backend.app.models.product import Product
from backend.app.models.price_history import PriceHistory
from backend.app.models.scrape_job import ScrapeJob
from backend.app.models.notification import Notification
from backend.worker.scrapers.base import ScrapeResult
from backend.worker.scrapers.bs4_scraper import BS4Scraper
from backend.worker.scrapers.playwright_scraper import PlaywrightScraper

logger = logging.getLogger(__name__)

_JS_PLATFORMS = {"getyourguide", "booking", "airbnb", "expedia", "hepsiburada"}


def _pick_scraper(platform: str | None) -> tuple[str, object]:
    if platform and platform.lower() in _JS_PLATFORMS:
        return "playwright", PlaywrightScraper()
    return "bs4", BS4Scraper()


async def scrape_product(ctx: dict, product_id: str, job_id: str | None = None) -> dict:
    logger.info("Starting scrape for product %s (job_id=%s)", product_id, job_id)

    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        logger.error("Invalid product_id: %r", product_id)
        return {"status": "error", "error": "invalid product_id"}

    async with async_session_factory() as session:
        stmt = (
            select(Product)
            .where(Product.id == pid)
            .options(selectinload(Product.alert_rules))
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if product is None:
            logger.warning("Product %s not found", product_id)
            return {"status": "error", "error": "product not found"}

        if not product.is_active:
            return {"status": "skipped", "reason": "inactive"}

        stype, scraper = _pick_scraper(product.platform)

        if job_id:
            job = await session.get(ScrapeJob, uuid.UUID(job_id))
            if job:
                job.status = "running"
                job.scraper_type = stype
                job.started_at = datetime.now(timezone.utc)
            else:
                job = ScrapeJob(
                    product_id=product.id,
                    status="running",
                    scraper_type=stype,
                    started_at=datetime.now(timezone.utc),
                )
                session.add(job)
        else:
            job = ScrapeJob(
                product_id=product.id,
                status="running",
                scraper_type=stype,
                started_at=datetime.now(timezone.utc),
            )
            session.add(job)
        await session.flush()

        old_price = product.current_price
        scrape_res: ScrapeResult | None = None

        try:
            scrape_res = await scraper.scrape(
                url=product.url,
                platform=product.platform,
                custom_selector=product.custom_selector,
            )
        except Exception as exc:
            logger.exception("Scraper raised an unhandled exception")
            scrape_res = ScrapeResult(
                price=None,
                currency=product.currency or "USD",
                status="error",
                error_message=str(exc)[:500],
            )

        # retry with playwright if bs4 cant find anything on unknown platform
        if (
            scrape_res.status == "not_found"
            and stype == "bs4"
            and product.platform is None
        ):
            logger.info("BS4 failed for unknown platform, retrying with Playwright: %s", product.url)
            stype = "playwright"
            pw = PlaywrightScraper()
            try:
                pw_result = await pw.scrape(
                    url=product.url,
                    platform=product.platform,
                    custom_selector=product.custom_selector,
                )
                if pw_result.status == "success" and pw_result.price is not None:
                    scrape_res = pw_result
                    job.scraper_type = "playwright"
            except Exception as exc:
                logger.warning("Playwright fallback also failed: %s", exc)

        now = datetime.now(timezone.utc)

        price_entry = PriceHistory(
            product_id=product.id,
            price=scrape_res.price if scrape_res.price is not None else Decimal("0"),
            currency=scrape_res.currency,
            scraped_at=now,
            status=scrape_res.status,
            error_message=scrape_res.error_message,
        )
        session.add(price_entry)

        if scrape_res.status == "success" and scrape_res.price is not None:
            product.current_price = scrape_res.price
            product.currency = scrape_res.currency

        if scrape_res.page_title and "." in product.name and " " not in product.name:
            product.name = scrape_res.page_title

        product.last_scraped_at = now
        product.next_scrape_at = now + product.scrape_interval

        if (
            scrape_res.status == "success"
            and scrape_res.price is not None
            and old_price is not None
        ):
            await _evaluate_alerts(session, product, old_price, scrape_res.price)

        job.status = scrape_res.status if scrape_res.status != "not_found" else "failed"
        if scrape_res.status == "success":
            job.status = "success"
        job.error_message = scrape_res.error_message
        job.completed_at = datetime.now(timezone.utc)

        await session.commit()

        logger.info(
            "Scrape complete for product %s: status=%s price=%s %s",
            product_id, scrape_res.status, scrape_res.price, scrape_res.currency,
        )

        return {
            "status": scrape_res.status,
            "price": str(scrape_res.price) if scrape_res.price else None,
            "currency": scrape_res.currency,
            "error": scrape_res.error_message,
        }


async def _evaluate_alerts(
    session,
    product: Product,
    old_price: Decimal,
    new_price: Decimal,
) -> None:
    if not product.alert_rules:
        return

    for rule in product.alert_rules:
        if not rule.is_active:
            continue

        triggered = False
        title = ""
        msg = ""

        if rule.rule_type == "price_below" and rule.target_price is not None:
            if new_price <= rule.target_price:
                triggered = True
                title = f"Price alert: {product.name}"
                msg = (
                    f"The price of {product.name} dropped to "
                    f"{product.currency} {new_price} "
                    f"(below your target of {product.currency} {rule.target_price})."
                )

        elif rule.rule_type == "price_above" and rule.target_price is not None:
            if new_price >= rule.target_price:
                triggered = True
                title = f"Price alert: {product.name}"
                msg = (
                    f"The price of {product.name} rose to "
                    f"{product.currency} {new_price} "
                    f"(above your target of {product.currency} {rule.target_price})."
                )

        elif rule.rule_type == "price_drop_pct" and rule.pct_threshold is not None:
            if old_price > 0:
                drop_pct = ((old_price - new_price) / old_price) * 100
                if drop_pct >= rule.pct_threshold:
                    triggered = True
                    title = "Price drop: {}".format(product.name)
                    msg = (
                        f"The price of {product.name} dropped by {drop_pct:.1f}% "
                        f"from {product.currency} {old_price} to "
                        f"{product.currency} {new_price}."
                    )

        elif rule.rule_type == "price_change":
            if new_price != old_price:
                triggered = True
                direction = "dropped" if new_price < old_price else "rose"
                title = f"Price change: {product.name}"
                msg = (
                    f"The price of {product.name} {direction} "
                    f"from {product.currency} {old_price} to "
                    f"{product.currency} {new_price}."
                )

        if triggered:
            notification = Notification(
                user_id=rule.user_id,
                product_id=product.id,
                alert_rule_id=rule.id,
                title=title,
                message=msg,
                old_price=old_price,
                new_price=new_price,
            )
            session.add(notification)
            logger.info(
                "Alert triggered: rule=%s type=%s product=%s",
                rule.id, rule.rule_type, product.id,
            )
