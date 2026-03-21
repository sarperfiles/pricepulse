from __future__ import annotations

import re
import json
import logging
from collections import Counter
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.worker.scrapers.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)

_CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₹": "INR",
    "R$": "BRL",
    "A$": "AUD",
    "C$": "CAD",
    "CHF": "CHF",
    "kr": "SEK",
    "zł": "PLN",
    "Kč": "CZK",
    "₺": "TRY",
}

_PRICE_PATTERN = re.compile(
    r"(?:From\s+)?"
    r"(?:(?:US)?\$|€|£|¥|₹|R\$|A\$|C\$|CHF|kr|zł|Kč|₺)\s*"
    r"([\d]{1,7}(?:[.,]\d{1,3})*)"
    r"|"
    r"([\d]{1,7}(?:[.,]\d{1,3})*)\s*"
    r"(?:€|£|\$|CHF|kr|zł|Kč|₺)",
    re.UNICODE,
)

_CURRENCY_PATTERN = re.compile(
    r"(US\$|\$|€|£|¥|₹|R\$|A\$|C\$|CHF|kr|zł|Kč|₺|USD|EUR|GBP|JPY|INR|BRL|AUD|CAD|SEK|NOK|DKK|PLN|CZK|TRY)",
    re.UNICODE,
)


def _parse_price(raw: str) -> Decimal | None:
    if not raw:
        return None
    cleaned = re.sub(r"[^\d.,]", "", raw.strip())
    if not cleaned:
        return None

    try:
        if "," in cleaned and "." in cleaned:
            if cleaned.rindex(",") > cleaned.rindex("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")

        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        logger.warning("Failed to parse price from: %r", raw)
        return None


def _detect_currency(text: str) -> str:
    match = _CURRENCY_PATTERN.search(text)
    if match:
        sym = match.group(1)
        if len(sym) == 3 and sym.isalpha():
            return sym.upper()
        return _CURRENCY_SYMBOLS.get(sym, "EUR")
    return "EUR"


def _extract_from_json_ld(html: str) -> tuple[Decimal | None, str]:
    pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(html):
        try:
            data = json.loads(m.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            result = _walk_json_ld_item(item)
            if result[0] is not None:
                return result

    return None, "EUR"


def _walk_json_ld_item(item: dict) -> tuple[Decimal | None, str]:
    if not isinstance(item, dict):
        return None, "EUR"

    price, currency = _try_extract_offer_price(item)
    if price is not None:
        return price, currency

    offers = item.get("offers")
    if offers:
        if isinstance(offers, dict):
            offers = [offers]
        if isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict):
                    price, currency = _try_extract_offer_price(offer)
                    if price is not None:
                        return price, currency

    graph = item.get("@graph")
    if isinstance(graph, list):
        for node in graph:
            if isinstance(node, dict):
                result = _walk_json_ld_item(node)
                if result[0] is not None:
                    return result

    return None, "EUR"


def _try_extract_offer_price(obj: dict) -> tuple[Decimal | None, str]:
    currency = obj.get("priceCurrency", "EUR")

    for key in ("price", "lowPrice", "highPrice"):
        raw = obj.get(key)
        if raw is not None:
            price = _parse_price(str(raw))
            if price is not None:
                return price, currency

    spec = obj.get("priceSpecification")
    if isinstance(spec, dict):
        currency = spec.get("priceCurrency", currency)
        raw = spec.get("price")
        if raw is not None:
            price = _parse_price(str(raw))
            if price is not None:
                return price, currency

    return None, currency


def _extract_from_next_data(html: str) -> tuple[Decimal | None, str]:
    pat = re.compile(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    match = pat.search(html)
    if not match:
        return None, "EUR"

    try:
        data = json.loads(match.group(1).strip())
    except (json.JSONDecodeError, ValueError):
        return None, "EUR"

    return _search_next_data_prices(data)


def _search_next_data_prices(data: Any, depth: int = 0) -> tuple[Decimal | None, str]:
    if depth > 15:
        return None, "EUR"

    if isinstance(data, dict):
        price_keys = [
            "fromPrice", "currentPrice", "price", "rawPrice",
            "retailPrice", "displayPrice", "amount", "basePrice",
            "lowestPrice", "startingPrice",
        ]
        currency_keys = ["currency", "currencyCode", "priceCurrency"]

        currency = "EUR"
        for ck in currency_keys:
            if ck in data and isinstance(data[ck], str) and len(data[ck]) == 3:
                currency = data[ck]
                break

        for key in ("price", "fromPrice", "currentPrice", "retailPrice", "lowestPrice"):
            val = data.get(key)
            if isinstance(val, dict):
                amt = val.get("amount") or val.get("value") or val.get("raw")
                cur = val.get("currency") or val.get("currencyCode") or currency
                if amt is not None:
                    price = _parse_price(str(amt))
                    if price is not None:
                        return price, cur if isinstance(cur, str) else currency

        for pk in price_keys:
            val = data.get(pk)
            if val is not None and not isinstance(val, (dict, list)):
                price = _parse_price(str(val))
                if price is not None:
                    return price, currency

        priority_keys = [
            "pageProps", "props", "activity", "product", "tour",
            "offer", "offers", "pricing", "data", "result",
            "dehydratedState", "queries",
        ]
        for pk in priority_keys:
            if pk in data:
                result = _search_next_data_prices(data[pk], depth + 1)
                if result[0] is not None:
                    return result

        for k, v in data.items():
            if k in priority_keys:
                continue
            if isinstance(v, (dict, list)):
                result = _search_next_data_prices(v, depth + 1)
                if result[0] is not None:
                    return result

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                result = _search_next_data_prices(item, depth + 1)
                if result[0] is not None:
                    return result

    return None, "EUR"


def _extract_from_dom_selectors(html: str) -> tuple[Decimal | None, str]:
    selector_patterns = [
        r'data-testid="[^"]*price[^"]*"[^>]*>([^<]*(?:€|\$|£|CHF|kr)\s*[\d.,]+[^<]*)<',
        r'data-testid="[^"]*price[^"]*"[^>]*>([^<]*[\d.,]+\s*(?:€|\$|£|CHF|kr)[^<]*)<',
        r'class="[^"]*price[^"]*"[^>]*>([^<]*(?:€|\$|£|CHF|kr)\s*[\d.,]+[^<]*)<',
        r'class="[^"]*price[^"]*"[^>]*>([^<]*[\d.,]+\s*(?:€|\$|£|CHF|kr)[^<]*)<',
        r'(?:From|Ab|Desde|À partir de|Da)\s+((?:€|\$|£)\s*[\d.,]+)',
        r'(?:From|Ab|Desde|À partir de|Da)\s+([\d.,]+\s*(?:€|\$|£))',
    ]

    for pattern in selector_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match_text in matches:
            price = _parse_price(match_text)
            if price is not None and price > 0:
                currency = _detect_currency(match_text)
                return price, currency

    return None, "EUR"


def _extract_from_regex_fallback(html: str) -> tuple[Decimal | None, str]:
    from_patterns = [
        r'(?:From|Ab|Desde|À partir de|Da)\s+(?:US\$|€|£|\$|CHF|kr|₺)\s*([\d.,]+)',
        r'(?:From|Ab|Desde|À partir de|Da)\s+([\d.,]+)\s*(?:€|£|\$|CHF|kr|₺)',
    ]
    for pattern in from_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            price = _parse_price(match.group(1))
            if price is not None and price > 0:
                start = max(0, match.start() - 20)
                end = min(len(html), match.end() + 20)
                ctx = html[start:end]
                currency = _detect_currency(ctx)
                return price, currency

    general_pattern = re.compile(
        r'(?:US\$|€|£|\$)\s*([\d]{1,7}(?:[.,]\d{1,3})*)'
        r'|([\d]{1,7}(?:[.,]\d{1,3})*)\s*(?:€|£|\$)',
        re.UNICODE,
    )
    candidates: list[tuple[Decimal, str]] = []
    for match in general_pattern.finditer(html):
        raw = match.group(1) or match.group(2)
        price = _parse_price(raw)
        if price is not None and Decimal("1") <= price <= Decimal("99999"):
            start = max(0, match.start() - 30)
            end = min(len(html), match.end() + 30)
            ctx = html[start:end]
            currency = _detect_currency(ctx)
            candidates.append((price, currency))

    if candidates:
        price_counts = Counter(c[0] for c in candidates)
        most_common_price = price_counts.most_common(1)[0][0]
        for p, c in candidates:
            if p == most_common_price:
                return p, c

    return None, "EUR"


# TODO: clean this up
def _extract_from_meta_tags(html: str) -> tuple[Decimal | None, str]:
    patterns = [
        r'<meta[^>]*(?:property|name)=["\'](?:og:price:amount|product:price:amount)["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:og:price:amount|product:price:amount)["\']',
    ]
    currency_patterns = [
        r'<meta[^>]*(?:property|name)=["\'](?:og:price:currency|product:price:currency)["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:og:price:currency|product:price:currency)["\']',
    ]

    price = None
    currency = "EUR"

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            price = _parse_price(match.group(1))
            break

    for pattern in currency_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            currency = match.group(1).strip().upper()
            break

    return price, currency


class GetYourGuideExtractor(BaseExtractor):

    async def extract_from_html(
        self, html: str, url: str, custom_selector: str | None = None
    ) -> tuple[Decimal | None, str]:
        return self._run_strategies(html)

    async def extract_from_page(
        self, page: Any, url: str, custom_selector: str | None = None
    ) -> tuple[Decimal | None, str]:
        html = await page.content()

        price, currency = await self._extract_from_rendered_dom(page)
        if price is not None:
            return price, currency

        return self._run_strategies(html)

    def _run_strategies(self, html: str) -> tuple[Decimal | None, str]:
        strategies = [
            ("JSON-LD", _extract_from_json_ld),
            ("__NEXT_DATA__", _extract_from_next_data),
            ("Meta tags", _extract_from_meta_tags),
            ("DOM selectors", _extract_from_dom_selectors),
            ("Regex fallback", _extract_from_regex_fallback),
        ]

        for name, strat in strategies:
            try:
                price, currency = strat(html)
                if price is not None:
                    logger.info("GYG: found price via %s: %s %s", name, price, currency)
                    return price, currency
            except Exception:
                logger.exception("GYG: strategy %s raised an error", name)
                continue

        logger.warning("GYG: all strategies failed")
        return None, "EUR"

    async def _extract_from_rendered_dom(
        self, page: Any
    ) -> tuple[Decimal | None, str]:
        try:
            await page.wait_for_selector(
                '[class*="price"], [data-testid*="price"]',
                timeout=5000,
            )
            await page.wait_for_timeout(500)
        except Exception:
            pass

        prices = await page.evaluate("""() => {
            const results = [];
            const els = document.querySelectorAll(
                '[class*="price"], [class*="Price"], [data-testid*="price"]'
            );
            for (const el of els) {
                const childPriceEls = el.querySelectorAll(
                    '[class*="price"], [class*="Price"], [data-testid*="price"]'
                );
                if (childPriceEls.length > 0) continue;

                const text = el.textContent?.trim();
                if (text && /[€$£¥₹]/.test(text) && /\\d/.test(text)) {
                    results.push(text);
                }
            }
            const perPerson = document.querySelectorAll('[class*="price"]');
            for (const el of perPerson) {
                const text = el.textContent?.trim();
                if (text && text.includes('per person') && /[€$£¥₹]/.test(text)) {
                    const match = text.match(/[€$£¥₹]\\s*[\\d.,]+/g);
                    if (match) {
                        results.unshift(match[match.length - 1]);
                    }
                }
            }
            return results;
        }""")

        for text in prices:
            price = _parse_price(text)
            if price is not None and Decimal("1") <= price <= Decimal("9999"):
                currency = _detect_currency(text)
                return price, currency

        return None, "EUR"
