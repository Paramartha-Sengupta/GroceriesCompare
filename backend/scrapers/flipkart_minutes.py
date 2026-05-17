import httpx
from .base import BaseScraper, ScrapeResult, ScrapedItem, MOBILE_UA


class FlipkartMinutesScraper(BaseScraper):
    platform_name = "Flipkart Minutes"

    async def _scrape_query(self, client: httpx.AsyncClient, query: str, lat: float, lon: float) -> ScrapeResult:
        headers = {
            "User-Agent": MOBILE_UA,
            "Accept": "application/json",
            "X-User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 FKUA/app/42/42.0/ios; Mobile",
            "Origin": "https://minutes.flipkart.com",
            "Referer": "https://minutes.flipkart.com/",
        }
        try:
            r = await client.get(
                "https://minutes.flipkart.com/api/4/page",
                params={"q": query, "type": "search"},
                headers=headers,
                timeout=15,
            )
            r.raise_for_status()
            body = r.json()
            products = (
                body.get("data", {}).get("products") or
                body.get("products") or body.get("items") or []
            )
            return ScrapeResult(
                platform=self.platform_name, query=query,
                items=self._parse(query, products)
            )
        except Exception as e:
            return ScrapeResult(platform=self.platform_name, query=query, error=str(e))

    def _parse(self, query: str, raw: list) -> list[ScrapedItem]:
        items, seen = [], set()
        for p in raw:
            try:
                if not isinstance(p, dict): continue
                name = p.get("name") or p.get("title") or p.get("productName") or ""
                if not name or name in seen: continue
                seen.add(name)
                price = float(p.get("price") or p.get("sellingPrice") or p.get("finalPrice") or p.get("mrp") or 0)
                if price > 5000: price /= 100
                unit = str(p.get("quantity") or p.get("unit") or p.get("weight") or "")
                image = p.get("image") or p.get("imageUrl") or ""
                items.append(ScrapedItem(
                    platform=self.platform_name, search_query=query,
                    name=name.strip(), price=price, unit=unit.strip(), image_url=image,
                ))
                if len(items) >= 5: break
            except Exception: continue
        return items
