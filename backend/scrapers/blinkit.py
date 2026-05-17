import re
import httpx
from .base import BaseScraper, ScrapeResult, ScrapedItem, MOBILE_UA


class BlinkitScraper(BaseScraper):
    platform_name = "Blinkit"

    async def _scrape_query(self, client: httpx.AsyncClient, query: str, lat: float, lon: float) -> ScrapeResult:
        headers = {
            "app_client": "consumer_web",
            "lat": str(lat),
            "lon": str(lon),
            "User-Agent": MOBILE_UA,
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://blinkit.com",
            "Referer": "https://blinkit.com/",
        }
        try:
            r = await client.get(
                "https://blinkit.com/v6/search/",
                params={"q": query, "start": 0, "size": 20},
                headers=headers,
                timeout=15,
            )
            r.raise_for_status()
            body = r.json()
            products = []
            # v6: body.products.objects or body.snippets
            if isinstance(body, dict):
                objects = (body.get("products") or {}).get("objects") or []
                if objects:
                    products = objects
                else:
                    for key in ("snippets", "data", "items"):
                        val = body.get(key)
                        if isinstance(val, list) and val:
                            products = val
                            break
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
                name = p.get("name") or p.get("product_name") or p.get("display_name") or ""
                if not name or name in seen: continue
                seen.add(name)
                price_raw = (p.get("price") or p.get("mrp") or p.get("sp") or
                             (p.get("pricing") or {}).get("price") or 0)
                price = float(price_raw)
                if price > 5000: price /= 100
                unit = str(p.get("unit") or p.get("quantity") or p.get("unit_quantity") or "")
                image = p.get("image") or p.get("image_url") or ""
                items.append(ScrapedItem(
                    platform=self.platform_name, search_query=query,
                    name=name.strip(), price=price, unit=unit.strip(), image_url=image,
                ))
                if len(items) >= 5: break
            except Exception: continue
        return items
