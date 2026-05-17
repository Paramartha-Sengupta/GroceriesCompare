import asyncio
import re
from playwright.async_api import Page
from .base import BaseScraper, ScrapeResult, ScrapedItem


class BigBasketScraper(BaseScraper):
    platform_name = "BigBasket"
    base_url = "https://www.bigbasket.com"

    async def set_location(self, page: Page, pincode: str) -> None:
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        try:
            # BigBasket shows a pincode/city modal on first visit
            loc_btn = page.locator("[id*='pincode'], button[class*='location'], [data-testid*='pincode']")
            await loc_btn.first.click(timeout=4000)
            await asyncio.sleep(0.5)
        except Exception:
            pass

        try:
            inp = page.locator("input[placeholder*='pincode'], input[id*='pincode'], input[placeholder*='PIN']")
            await inp.first.fill(pincode, timeout=4000)
            await asyncio.sleep(0.5)
            proceed = page.locator("button:has-text('Proceed'), button:has-text('Go'), button[type='submit']")
            if await proceed.count() > 0:
                await proceed.first.click(timeout=3000)
            else:
                await page.keyboard.press("Enter")
            await asyncio.sleep(2)
        except Exception:
            pass

    async def _scrape_query(self, page: Page, query: str) -> ScrapeResult:
        captured_products: list[dict] = []

        async def capture_response(response):
            url = response.url
            if "bigbasket.com" in url and ("listing" in url or "search" in url or "product" in url):
                try:
                    body = await response.json()
                    if isinstance(body, dict):
                        # v2 listing: body.tab_info[].prod_list[]
                        for tab in body.get("tab_info") or [body]:
                            prods = tab.get("prod_list") or []
                            if prods:
                                captured_products.extend(prods)
                                break
                        # flat fallbacks
                        for key in ("products", "data", "items", "results"):
                            val = body.get(key)
                            if isinstance(val, list) and val:
                                captured_products.extend(val)
                                break
                except Exception:
                    pass

        page.on("response", capture_response)
        try:
            await page.goto(
                f"{self.base_url}/ps/?q={query.replace(' ', '%20')}",
                wait_until="networkidle", timeout=30000,
            )
        except Exception:
            try:
                await page.goto(
                    f"{self.base_url}/ps/?q={query.replace(' ', '%20')}",
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
                name = p.get("desc") or p.get("name") or p.get("product_name") or ""
                if not name or name in seen:
                    continue
                seen.add(name)
                pricing = p.get("pricing") or {}
                disc = (pricing.get("discount") or {})
                price = float(
                    disc.get("dsc_prc")
                    or pricing.get("np")
                    or p.get("sp") or p.get("price") or p.get("mrp") or 0
                )
                unit = str(p.get("w") or p.get("unit") or p.get("qty") or "")
                image = (p.get("images") or [{}])[0].get("s") or p.get("image") or ""
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
                "li[class*='ProdList'], div[class*='SKU'], div[class*='product-card']",
                timeout=6000,
            )
            cards = page.locator("li[class*='ProdList'], div[class*='SKU']")
            for i in range(min(await cards.count(), 5)):
                card = cards.nth(i)
                try:
                    name = await card.locator("[class*='prod-name'], [class*='Name'], h3").first.inner_text(timeout=2000)
                    price_text = await card.locator("[class*='discnt-price'], [class*='sp--'], [class*='price']").first.inner_text(timeout=2000)
                    price = float(re.sub(r"[^\d.]", "", price_text.split("\n")[0]))
                    unit = ""
                    try:
                        unit = await card.locator("[class*='weight'], [class*='pack-size']").first.inner_text(timeout=1000)
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
