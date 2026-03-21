from __future__ import annotations

import logging

from patchright.async_api import async_playwright
from browserforge.headers import HeaderGenerator

from backend.worker.scrapers.base import BaseScraper, ScrapeResult
from backend.worker.scrapers.extractors import get_extractor

logger = logging.getLogger(__name__)

_NAV_TIMEOUT = 30_000
_RENDER_WAIT = 3_000


async def _get_page_title(page) -> str | None:
    try:
        result = await page.evaluate("""() => {
            const ldScripts = document.querySelectorAll('script[type="application/ld+json"]');
            for (const s of ldScripts) {
                try {
                    const data = JSON.parse(s.textContent);
                    const items = Array.isArray(data) ? data : [data];
                    for (const item of items) {
                        if (item && item.name && typeof item.name === 'string' && item.name.length > 3)
                            return item.name.trim().slice(0, 255);
                    }
                } catch {}
            }
            const og = document.querySelector('meta[property="og:title"]');
            if (og && og.content && og.content.length > 3) return og.content.trim().slice(0, 255);
            const h1 = document.querySelector('h1');
            if (h1 && h1.textContent.trim().length > 3) return h1.textContent.trim().slice(0, 255);
            const title = document.title;
            if (title) {
                for (const sep of [' | ', ' - ', ' – ', ' — ', ' :: ']) {
                    if (title.includes(sep)) return title.split(sep)[0].trim().slice(0, 255);
                }
                if (title.length > 3) return title.trim().slice(0, 255);
            }
            return null;
        }""")
        return result
    except Exception:
        return None


def _generate_fingerprint() -> dict:
    gen = HeaderGenerator(browser="chrome", os=("windows", "macos", "linux"))
    headers = gen.generate()
    return {
        "user_agent": headers.get("User-Agent", ""),
        "accept_language": headers.get("Accept-Language", "en-US,en;q=0.9"),
        "headers": {k: v for k, v in headers.items() if k.lower() in ("accept-language", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform")},
    }


class PlaywrightScraper(BaseScraper):

    async def scrape(
        self,
        url: str,
        platform: str | None = None,
        custom_selector: str | None = None,
    ) -> ScrapeResult:
        extractor = get_extractor(platform)
        fp = _generate_fingerprint()

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-gpu",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent=fp["user_agent"],
                    locale="en-US",
                    extra_http_headers={
                        "Accept-Language": fp["accept_language"],
                        **fp["headers"],
                    },
                )

                page = await context.new_page()

                logger.info("Navigating to %s", url)
                try:
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=_NAV_TIMEOUT,
                    )
                except Exception as nav_err:
                    logger.warning("Navigation issue (may still proceed): %s", nav_err)

                try:
                    await page.wait_for_load_state("networkidle", timeout=_RENDER_WAIT)
                except Exception:
                    pass

                # wait a bit for late-loading price widgets
                try:
                    await page.wait_for_timeout(1500)
                except Exception:
                    pass

                price, currency = await extractor.extract_from_page(
                    page, url, custom_selector
                )

                page_title = await _get_page_title(page)

                await browser.close()

                if price is not None:
                    return ScrapeResult(price=price, currency=currency, status="success", page_title=page_title)
                return ScrapeResult(
                    price=None,
                    currency=currency,
                    status="not_found",
                    error_message="Price not found on page",
                    page_title=page_title,
                )

        except Exception as exc:
            logger.exception("Scraper failed for %s", url)
            return ScrapeResult(
                price=None,
                currency="USD",
                status="error",
                error_message=str(exc)[:500],
            )
