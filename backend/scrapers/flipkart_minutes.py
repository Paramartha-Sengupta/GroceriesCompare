import asyncio
import re
from playwright.async_api import Page
from .base import BaseScraper, ScrapeResult, ScrapedItem


class FlipkartMinutesScraper(BaseScraper):
    platform_name = "Flipkart Minutes"
    base_url = "https://minutes.flipkart.com"

    async def set_location(self, page: Page, pincode: str) -> None:
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        try:
            inp = page.locator("input[placeholder*='pincode'], input[placeholder*='Enter pincode']")
            await inp.first.fill(pincode, timeout=4000)
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)
        except Exception:
            pass

    async def _scrape_query(self, page: Page, query: str) -> ScrapeResult:
        captured_products: list[dict] = []

        async def capture_response(response):
            url = response.url
            if "flipkart.com" in url and ("search" in url or "listing" in url or "product" in url):
                try:
                    body = await response.json()
                    # Flipkart Minutes: { data: { products: [] } }
                    prods = (
                        body.get("data", {}).get("products")
                        or body.get("products")
                        or body.get("items") or []
                    )
                    captured_products.extend(prods)
                except Exception:
                    pass

        page.on("response", capture_response)
        try:
            await page.goto(
                f"{self.base_url}/search?q={query.replace(' ', '%20')}",
                wait_until="networkidle", timeout=30000,
            )
        except Exception:
            try:
                await page.goto(
                    f"{self.base_url}/search?q={query.replace(' ', '%20')}",
                    wait_until="domcontentloaded", timeout=30000,
                )
                await asyncio.sleep(3)
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
                name = p.get("name") or p.get("title") or p.get("productName") or ""
                if not name or name in seen:
                    continue
                seen.add(name)
                price = float(
                    p.get("price") or p.get("sellingPrice")
                    or p.get("finalPrice") or p.get("mrp") or 0
                )
                if price > 5000:
                    price /= 100
                unit = str(p.get("quantity") or p.get("unit") or p.get("weight") or "")
                image = p.get("image") or p.get("imageUrl") or ""
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
            await page.wait_for_selector("div[class*='product'], div[class*='Product']", timeout=6000)
            cards = page.locator("div[class*='ProductCard'], div[class*='product-card']")
            for i in range(min(await cards.count(), 5)):
                card = cards.nth(i)
                try:
                    name = await card.locator("[class*='name'], [class*='title'], h3").first.inner_text(timeout=2000)
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
