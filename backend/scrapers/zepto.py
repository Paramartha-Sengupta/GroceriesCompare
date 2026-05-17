import asyncio
import re
from playwright.async_api import Page
from .base import BaseScraper, ScrapeResult, ScrapedItem


class ZeptoScraper(BaseScraper):
    platform_name = "Zepto"
    base_url = "https://www.zeptonow.com"

    async def set_location(self, page: Page, pincode: str) -> None:
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        try:
            await page.click("[class*='LocationBar'], button[class*='location'], [data-testid*='location']", timeout=3000)
            await asyncio.sleep(0.5)
        except Exception:
            pass

        try:
            inp = page.locator("input[placeholder*='pincode'], input[placeholder*='Enter pincode']")
            await inp.first.fill(pincode, timeout=4000)
            await asyncio.sleep(0.5)
            suggestion = page.locator("[class*='suggestion'], [class*='Suggestion'], li[class*='pin']")
            if await suggestion.count() > 0:
                await suggestion.first.click(timeout=3000)
            else:
                await page.keyboard.press("Enter")
            await asyncio.sleep(2)
        except Exception:
            pass

    async def _scrape_query(self, page: Page, query: str) -> ScrapeResult:
        captured_products: list[dict] = []

        async def capture_response(response):
            url = response.url
            if "zeptonow.com" in url and ("search" in url or "product" in url or "catalog" in url):
                try:
                    body = await response.json()
                    # Zepto response shape: { sections: [{ items: [{ product: {...} }] }] }
                    if isinstance(body, dict):
                        sections = body.get("sections") or body.get("data", {}).get("sections") or []
                        for section in sections:
                            for item_wrapper in section.get("items") or []:
                                p = item_wrapper.get("product") or item_wrapper
                                if isinstance(p, dict) and p.get("name"):
                                    captured_products.append(p)
                        # Flat list fallback
                        for key in ("products", "items", "results", "data"):
                            val = body.get(key)
                            if isinstance(val, list):
                                captured_products.extend(val)
                                break
                except Exception:
                    pass

        page.on("response", capture_response)
        try:
            await page.goto(
                f"{self.base_url}/search?query={query.replace(' ', '%20')}",
                wait_until="networkidle", timeout=30000,
            )
        except Exception:
            try:
                await page.goto(
                    f"{self.base_url}/search?query={query.replace(' ', '%20')}",
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
                name = p.get("name") or p.get("product_name") or ""
                if not name or name in seen:
                    continue
                seen.add(name)
                price = float(
                    p.get("discountedSellingPrice")
                    or p.get("sellingPrice")
                    or p.get("price")
                    or p.get("mrp") or 0
                )
                if price > 5000:
                    price /= 100
                unit = str(
                    p.get("unitQuantity") or p.get("quantity")
                    or p.get("unit") or p.get("weight") or ""
                )
                image = p.get("imageUrl") or p.get("image") or ""
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
                "[data-testid='product-card'], div[class*='ProductCard'], div[class*='product-card']",
                timeout=6000,
            )
            cards = page.locator("[data-testid='product-card'], div[class*='ProductCard']")
            for i in range(min(await cards.count(), 5)):
                card = cards.nth(i)
                try:
                    name = await card.locator("h5, h4, [class*='name']").first.inner_text(timeout=2000)
                    price_text = await card.locator("[class*='price'], [class*='Price']").first.inner_text(timeout=2000)
                    price = float(re.sub(r"[^\d.]", "", price_text.split("\n")[0]))
                    unit = ""
                    try:
                        unit = await card.locator("[class*='weight'], [class*='quantity']").first.inner_text(timeout=1000)
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
