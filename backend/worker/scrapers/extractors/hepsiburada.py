from __future__ import annotations

import re
import json
import logging
from collections import Counter
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.worker.scrapers.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)

# _debug_mode = False


def _parse_price(raw: str) -> Decimal | None:
    cleaned = re.sub(r"[^\d.,]", "", raw.strip())
    if not cleaned:
        return None
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
    try:
        val = Decimal(cleaned)
        if Decimal("0.01") <= val <= Decimal("9999999"):
            return val
        return None
    except (InvalidOperation, ValueError):
        return None


class HepsiburadaExtractor(BaseExtractor):

    async def extract_from_html(
        self, html: str, url: str, custom_selector: str | None = None
    ) -> tuple[Decimal | None, str]:
        strategies = (
            self._from_json_ld,
            self._from_meta_tags,
            self._from_microdata,
            self._from_hb_classes,
            self._from_regex,
        )
        for strat in strategies:
            try:
                price, currency = strat(html)
                if price is not None:
                    return price, currency
            except Exception:
                continue
        return None, "TRY"

    async def extract_from_page(
        self, page: Any, url: str, custom_selector: str | None = None
    ) -> tuple[Decimal | None, str]:
        if custom_selector:
            try:
                el = await page.query_selector(custom_selector)
                if el:
                    text = await el.text_content()
                    if text:
                        price = _parse_price(text)
                        if price is not None:
                            return price, "TRY"
            except Exception:
                logger.debug("Custom selector %r failed", custom_selector)

        result = await self._extract_via_js(page)
        if result[0] is not None:
            return result

        selectors = [
            '[data-testid="price-current-price"]',
            '[data-testid="price"]',
            '[data-bind*="currentPrice"]',
            '[itemprop="price"]',
            'meta[property="product:price:amount"]',
            'span[class*="price" i]',
            'div[class*="price" i]',
            'span[class*="fiyat" i]',
            'div[class*="fiyat" i]',
            '#offering-price',
            '.product-price',
        ]

        for sel in selectors:
            try:
                elements = await page.query_selector_all(sel)
                for el in elements:
                    content = await el.get_attribute("content")
                    if content:
                        price = _parse_price(content)
                        if price is not None:
                            return price, "TRY"
                    text = await el.text_content()
                    if text:
                        price = _parse_price(text)
                        if price is not None:
                            return price, "TRY"
            except Exception:
                continue

        html = await page.content()
        return await self.extract_from_html(html, url, custom_selector)

    async def _extract_via_js(self, page: Any) -> tuple[Decimal | None, str]:
        try:
            result = await page.evaluate("""() => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                for (const s of scripts) {
                    try {
                        const data = JSON.parse(s.textContent);
                        const items = Array.isArray(data) ? data : [data];
                        const queue = [...items];
                        while (queue.length > 0) {
                            const item = queue.shift();
                            if (!item || typeof item !== 'object') continue;
                            if (item['@graph'] && Array.isArray(item['@graph'])) {
                                queue.push(...item['@graph']);
                            }
                            const offers = item.offers;
                            if (offers) {
                                const offerList = Array.isArray(offers) ? offers : [offers];
                                for (const o of offerList) {
                                    const p = o.price || o.lowPrice;
                                    if (p !== undefined && p !== null) {
                                        return { price: String(p), currency: o.priceCurrency || 'TRY' };
                                    }
                                }
                            }
                        }
                    } catch {}
                }

                const priceMeta = document.querySelector(
                    'meta[property="product:price:amount"], meta[property="og:price:amount"]'
                );
                if (priceMeta && priceMeta.content) {
                    return { price: priceMeta.content, currency: 'TRY' };
                }

                const itemPrice = document.querySelector('[itemprop="price"]');
                if (itemPrice) {
                    const val = itemPrice.content || itemPrice.textContent;
                    if (val) return { price: val.trim(), currency: 'TRY' };
                }

                const hbSelectors = [
                    '[data-testid="price-current-price"]',
                    '[data-testid="price"]',
                    '#offering-price',
                    'span[class*="price"]',
                    'span[class*="fiyat"]',
                    'div[class*="fiyat"]',
                ];
                const priceRe = /[\\d][\\d.,]*[\\d]/;
                for (const sel of hbSelectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const text = (el.textContent || '').trim();
                        if (text && priceRe.test(text)) {
                            return { price: text, currency: 'TRY' };
                        }
                    }
                }

                return null;
            }""")

            if result and result.get("price"):
                price = _parse_price(result["price"])
                if price is not None:
                    cur = result.get("currency", "TRY").strip().upper()
                    if cur == "TL":
                        cur = "TRY"
                    if not cur or len(cur) != 3:
                        cur = "TRY"
                    return price, cur
        except Exception:
            print("hepsiburada js extraction failed")  # TODO: better error handling

        return None, "TRY"

    def _from_json_ld(self, html: str) -> tuple[Decimal | None, str]:
        pat = re.compile(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE,
        )
        for match in pat.finditer(html):
            try:
                data = json.loads(match.group(1).strip())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    result = self._walk_json_ld(item)
                    if result[0] is not None:
                        return result
            except (json.JSONDecodeError, ValueError):
                continue
        return None, "TRY"

    def _walk_json_ld(self, item: Any, depth: int = 0) -> tuple[Decimal | None, str]:
        if depth > 10 or not isinstance(item, dict):
            return None, "TRY"

        offers = item.get("offers")
        if offers:
            offer_list = offers if isinstance(offers, list) else [offers]
            for o in offer_list:
                if isinstance(o, dict):
                    currency = o.get("priceCurrency", "TRY")
                    if isinstance(currency, str) and currency.upper() == "TL":
                        currency = "TRY"
                    for key in ("price", "lowPrice", "highPrice"):
                        raw = o.get(key)
                        if raw is not None:
                            price = _parse_price(str(raw))
                            if price is not None:
                                return price, currency

        graph = item.get("@graph")
        if isinstance(graph, list):
            for node in graph:
                result = self._walk_json_ld(node, depth + 1)
                if result[0] is not None:
                    return result

        return None, "TRY"

    def _from_meta_tags(self, html: str) -> tuple[Decimal | None, str]:
        price_patterns = [
            r'<meta[^>]*(?:property|name)=["\'](?:og:price:amount|product:price:amount)["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:og:price:amount|product:price:amount)["\']',
        ]
        for pat in price_patterns:
            match = re.search(pat, html, re.IGNORECASE)
            if match:
                price = _parse_price(match.group(1))
                if price is not None:
                    return price, "TRY"
        return None, "TRY"

    def _from_microdata(self, html: str) -> tuple[Decimal | None, str]:
        patterns = [
            r'<[^>]*itemprop=["\']price["\'][^>]*content=["\']([^"\']+)["\']',
            r'<[^>]*itemprop=["\']price["\'][^>]*>([^<]+)<',
        ]
        for pat in patterns:
            match = re.search(pat, html, re.IGNORECASE)
            if match:
                price = _parse_price(match.group(1))
                if price is not None:
                    return price, "TRY"
        return None, "TRY"

    def _from_hb_classes(self, html: str) -> tuple[Decimal | None, str]:
        patterns = [
            r'data-testid="price-current-price"[^>]*>([^<]+)<',
            r'data-testid="price"[^>]*>([^<]+)<',
            r'id="offering-price"[^>]*>([^<]+)<',
            r'class="[^"]*(?:price|fiyat)[^"]*"[^>]*>([^<]*(?:₺|TL)\s*[\d.,]+[^<]*)<',
            r'class="[^"]*(?:price|fiyat)[^"]*"[^>]*>([^<]*[\d.,]+\s*(?:₺|TL)[^<]*)<',
            r'class="[^"]*(?:price|fiyat)[^"]*"[^>]*>([^<]*[\d][\d.,]*[\d][^<]*)<',
        ]
        for pat in patterns:
            for match in re.finditer(pat, html, re.IGNORECASE):
                raw = match.group(1).strip()
                price = _parse_price(raw)
                if price is not None:
                    return price, "TRY"
        return None, "TRY"

    def _from_regex(self, html: str) -> tuple[Decimal | None, str]:
        patterns = [
            re.compile(r"₺\s*([\d]{1,7}(?:[.,]\d{1,3})*)", re.UNICODE),
            re.compile(r"([\d]{1,7}(?:[.,]\d{1,3})*)\s*(?:₺|TL|TRY)", re.IGNORECASE | re.UNICODE),
        ]
        candidates: list[Decimal] = []
        for pat in patterns:
            for match in pat.finditer(html):
                price = _parse_price(match.group(1))
                if price is not None:
                    candidates.append(price)

        if candidates:
            counts = Counter(candidates)
            return counts.most_common(1)[0][0], "TRY"

        return None, "TRY"
