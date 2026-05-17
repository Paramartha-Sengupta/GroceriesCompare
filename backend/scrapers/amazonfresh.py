import asyncio
import re
from playwright.async_api import Page
from .base import BaseScraper, ScrapeResult, ScrapedItem

FRESH_NODE = "5940050031"  # Amazon.in Fresh & Gourmet node


class AmazonFreshScraper(BaseScraper):
    platform_name = "AmazonFresh"
    base_url = "https://www.amazon.in"

    async def set_location(self, page: Page, pincode: str) -> None:
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        try:
            await page.click("#nav-global-location-popover-link, #glow-ingress-block", timeout=4000)
            await asyncio.sleep(1)
            inp = page.locator("input[id*='GLUXZipUpdateInput'], input[placeholder*='PIN'], input[placeholder*='zip']")
            await inp.first.fill(pincode, timeout=4000)
            apply = page.locator("input[aria-labelledby*='GLUXZipUpdate'], span:has-text('Apply'), button:has-text('Apply')")
            await apply.first.click(timeout=3000)
            await asyncio.sleep(2)
        except Exception:
            pass

    async def _scrape_query(self, page: Page, query: str) -> ScrapeResult:
        captured_products: list[dict] = []

        async def capture_response(response):
            url = response.url
            if "amazon.in" in url and ("s?" in url or "search" in url or "api" in url):
                try:
                    body = await response.json()
                    prods = (
                        body.get("searchResult", {}).get("items")
                        or body.get("results") or body.get("items") or []
                    )
                    captured_products.extend(prods)
                except Exception:
                    pass

        page.on("response", capture_response)
        search_url = f"{self.base_url}/s?k={query.replace(' ', '+')}&rh=n%3A{FRESH_NODE}&i=grocery"
        try:
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
        except Exception:
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
            except Exception as e:
                return ScrapeResult(platform=self.platform_name, query=query, error=str(e))
        page.remove_listener("response", capture_response)

        items = await self._dom_parse(page, query)
        return ScrapeResult(platform=self.platform_name, query=query, items=items)

    async def _dom_parse(self, page: Page, query: str) -> list[ScrapedItem]:
        """Amazon search page is server-rendered — DOM parsing is reliable here."""
        items = []
        try:
            await page.wait_for_selector("div[data-component-type='s-search-result']", timeout=6000)
            cards = page.locator("div[data-component-type='s-search-result']")
            for i in range(min(await cards.count(), 5)):
                card = cards.nth(i)
                try:
                    name = await card.locator("h2 span, h2 a span").first.inner_text(timeout=2000)
                    whole = await card.locator(".a-price-whole").first.inner_text(timeout=2000)
                    frac = "0"
                    try:
                        frac = await card.locator(".a-price-fraction").first.inner_text(timeout=1000)
                    except Exception:
                        pass
                    price = float(f"{re.sub(r'[^0-9]', '', whole)}.{frac.strip()}")
                    unit = ""
                    try:
                        unit = await card.locator(".a-size-base.a-color-secondary").first.inner_text(timeout=1000)
                    except Exception:
                        pass
                    image = ""
                    try:
                        image = await card.locator("img.s-image").first.get_attribute("src", timeout=1000) or ""
                    except Exception:
                        pass
                    items.append(ScrapedItem(
                        platform=self.platform_name, search_query=query,
                        name=name.strip(), price=price, unit=unit.strip(), image_url=image,
                    ))
                except Exception:
                    continue
        except Exception:
            pass
        return items
