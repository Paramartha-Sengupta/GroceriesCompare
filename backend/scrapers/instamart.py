import asyncio
import re
from playwright.async_api import Page
from .base import BaseScraper, ScrapeResult, ScrapedItem


class InstamartScraper(BaseScraper):
    platform_name = "Instamart"
    base_url = "https://www.swiggy.com/instamart"

    async def set_location(self, page: Page, pincode: str) -> None:
        await page.goto("https://www.swiggy.com", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        try:
            loc = page.locator("input[placeholder*='Search for area'], input[id*='location']")
            await loc.first.fill(pincode, timeout=5000)
            await asyncio.sleep(1)
            suggestion = page.locator("div[class*='sc-jSgupP'], div[class*='suggestion']")
            if await suggestion.count() > 0:
                await suggestion.first.click(timeout=3000)
            await asyncio.sleep(2)
        except Exception:
            pass

    async def _scrape_query(self, page: Page, query: str) -> ScrapeResult:
        captured_products: list[dict] = []

        async def capture_response(response):
            url = response.url
            if "swiggy.com" in url and ("search" in url or "instamart" in url or "grocery" in url):
                try:
                    body = await response.json()
                    if isinstance(body, dict):
                        # Instamart search: data.widgets[].data.products[]
                        widgets = (
                            body.get("data", {}).get("widgets")
                            or body.get("widgets") or []
                        )
                        for w in widgets:
                            prods = w.get("data", {}).get("products") or w.get("products") or []
                            captured_products.extend(prods)
                        for key in ("products", "items", "results"):
                            val = body.get(key)
                            if isinstance(val, list) and val:
                                captured_products.extend(val)
                                break
                except Exception:
                    pass

        page.on("response", capture_response)
        try:
            await page.goto(
                f"{self.base_url}/search?query={query.replace(' ', '%20')}",
                wait_until="networkidle", timeout=35000,
            )
        except Exception:
            try:
                await page.goto(
                    f"{self.base_url}/search?query={query.replace(' ', '%20')}",
                    wait_until="domcontentloaded", timeout=30000,
                )
                await asyncio.sleep(4)
            except Exception as e:
                return ScrapeResult(platform=self.platform_name, query=query, error=str(e))
        page.remove_listener("response", capture_response)

        items = self._parse_products(query, captured_products)
        if not items:
            items = await self._dom_fallback(page, query)
        return ScrapeResult(platform=self.platform_name, query=query, items=items)

    def _parse_products(self, query: str, raw: list[dict]) -> list[ScrapedItem]:
        items = []
        seen = set()
        for p in raw:
            try:
                name = p.get("name") or p.get("display_name") or ""
                if not name or name in seen:
                    continue
                seen.add(name)
                price = float(p.get("price") or p.get("instamart_price") or p.get("mrp") or 0)
                if price > 5000:
                    price /= 100
                unit = str(p.get("quantity") or p.get("unit") or p.get("weight") or "")
                image = p.get("image_id") or p.get("image") or ""
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
            await page.wait_for_selector("div[class*='Product'], div[class*='sc-']", timeout=6000)
            cards = page.locator("div[class*='ProductCard'], div[class*='product']")
            for i in range(min(await cards.count(), 5)):
                card = cards.nth(i)
                try:
                    name = await card.locator("[class*='name'], h3, h4").first.inner_text(timeout=2000)
                    price_text = await card.locator("[class*='price'], [class*='Price']").first.inner_text(timeout=2000)
                    price = float(re.sub(r"[^\d.]", "", price_text.split("\n")[0]))
                    items.append(ScrapedItem(
                        platform=self.platform_name, search_query=query,
                        name=name.strip(), price=price, unit="",
                    ))
                except Exception:
                    continue
        except Exception:
            pass
        return items
