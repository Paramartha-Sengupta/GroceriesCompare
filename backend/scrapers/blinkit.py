import asyncio
import json
import re
import httpx
from playwright.async_api import Page, Route
from .base import BaseScraper, ScrapeResult, ScrapedItem


class BlinkitScraper(BaseScraper):
    platform_name = "Blinkit"
    base_url = "https://blinkit.com"

    async def set_location(self, page: Page, pincode: str) -> None:
        captured: list[dict] = []

        async def intercept(route: Route):
            await route.continue_()

        await page.route("**/*", intercept)

        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Try setting pincode through the UI
        try:
            await page.click("text=Deliver to", timeout=4000)
            await asyncio.sleep(0.5)
        except Exception:
            try:
                await page.click("[class*='LocationBar'], [data-testid*='location']", timeout=3000)
            except Exception:
                pass

        try:
            inp = page.locator("input[placeholder*='pincode'], input[placeholder*='Enter'], input[type='tel']")
            await inp.first.fill(pincode, timeout=4000)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)
        except Exception:
            pass

        # Store lat/lon in cookies if available — Blinkit sets them
        self._pincode = pincode

    async def _scrape_query(self, page: Page, query: str) -> ScrapeResult:
        captured_products: list[dict] = []

        async def capture_response(response):
            url = response.url
            if ("search" in url or "product" in url) and ("blinkit.com" in url):
                try:
                    body = await response.json()
                    if isinstance(body, dict):
                        # v6 search: body.products.objects
                        objs = (body.get("products") or {}).get("objects") or []
                        if objs:
                            captured_products.extend(objs)
                        # v2 style
                        for key in ("data", "items", "results"):
                            items = body.get(key)
                            if isinstance(items, list) and items:
                                captured_products.extend(items)
                                break
                except Exception:
                    pass

        page.on("response", capture_response)

        try:
            await page.goto(
                f"{self.base_url}/s/?q={query.replace(' ', '%20')}",
                wait_until="networkidle", timeout=30000,
            )
        except Exception:
            try:
                await page.goto(
                    f"{self.base_url}/s/?q={query.replace(' ', '%20')}",
                    wait_until="domcontentloaded", timeout=30000,
                )
                await asyncio.sleep(3)
            except Exception as e:
                return ScrapeResult(platform=self.platform_name, query=query, error=str(e))

        page.remove_listener("response", capture_response)

        items = self._parse_products(query, captured_products)

        # Fallback: parse DOM if network interception yielded nothing
        if not items:
            items = await self._dom_fallback(page, query)

        return ScrapeResult(platform=self.platform_name, query=query, items=items)

    def _parse_products(self, query: str, raw: list[dict]) -> list[ScrapedItem]:
        items = []
        seen = set()
        for p in raw:
            try:
                name = p.get("name") or p.get("product_name") or p.get("display_name") or ""
                if not name or name in seen:
                    continue
                seen.add(name)
                # Price may be in paise or rupees depending on API version
                price_raw = (
                    p.get("price") or p.get("mrp") or p.get("sp") or
                    (p.get("pricing") or {}).get("price") or 0
                )
                price = float(price_raw)
                # Blinkit v6 returns paise when > 1000 and item costs < 1000
                if price > 5000:
                    price = price / 100
                unit = str(p.get("unit") or p.get("quantity") or p.get("unit_quantity") or "")
                image = p.get("image") or p.get("image_url") or ""
                items.append(ScrapedItem(
                    platform=self.platform_name, search_query=query,
                    name=name.strip(), price=price, unit=unit.strip(), image_url=image,
                ))
                if len(items) >= 5:
                    break
            except Exception:
                continue
        return items

    async def _dom_fallback(self, page: Page, query: str) -> list[ScrapedItem]:
        items = []
        try:
            await page.wait_for_selector(
                "[class*='Product'], [class*='product-card'], [data-testid*='product']",
                timeout=5000,
            )
            cards = page.locator(
                "[class*='UpdatedPlpProductCard'], [class*='product-card'], div[class*='Product__']"
            )
            for i in range(min(await cards.count(), 5)):
                card = cards.nth(i)
                try:
                    name = await card.locator(
                        "[class*='name'], [class*='Name'], h3, h4"
                    ).first.inner_text(timeout=2000)
                    price_text = await card.locator(
                        "[class*='Price'], [class*='price']"
                    ).first.inner_text(timeout=2000)
                    price = float(re.sub(r"[^\d.]", "", price_text.split("\n")[0]))
                    unit = ""
                    try:
                        unit = await card.locator("[class*='weight'], [class*='unit']").first.inner_text(timeout=1000)
                    except Exception:
                        pass
                    items.append(ScrapedItem(
                        platform=self.platform_name, search_query=query,
                        name=name.strip(), price=price, unit=unit.strip(),
                    ))
                except Exception:
                    continue
        except Exception:
            pass
        return items
