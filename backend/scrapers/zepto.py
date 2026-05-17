import httpx
from .base import BaseScraper, ScrapeResult, ScrapedItem, MOBILE_UA


class ZeptoScraper(BaseScraper):
    platform_name = "Zepto"

    async def _scrape_query(self, client: httpx.AsyncClient, query: str, lat: float, lon: float) -> ScrapeResult:
        headers = {
            "User-Agent": MOBILE_UA,
            "Accept": "application/json",
            "appVersion": "10.6.2",
            "deviceType": "3",
            "storeType": "1",
            "latitude": str(lat),
            "longitude": str(lon),
            "Origin": "https://www.zeptonow.com",
            "Referer": "https://www.zeptonow.com/",
        }
        try:
            r = await client.get(
                "https://api.zeptonow.com/api/v1/search",
                params={"query": query, "pageNumber": 0, "pageSize": 15, "version": 5},
                headers=headers,
                timeout=15,
            )
            r.raise_for_status()
            body = r.json()
            products = []
            if isinstance(body, dict):
                sections = body.get("sections") or body.get("data", {}).get("sections") or []
                for sec in sections:
                    for item in (sec.get("items") or []):
                        p = item.get("product") or item
                        if isinstance(p, dict) and p.get("name"):
                            products.append(p)
                if not products:
                    for key in ("products", "items", "results"):
                        val = body.get(key)
                        if isinstance(val, list) and val:
                            products = val; break
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
                name = p.get("name") or p.get("product_name") or ""
                if not name or name in seen: continue
                seen.add(name)
                price = float(p.get("discountedSellingPrice") or p.get("sellingPrice") or
                              p.get("price") or p.get("mrp") or 0)
                if price > 5000: price /= 100
                unit = str(p.get("unitQuantity") or p.get("quantity") or p.get("unit") or "")
                image = p.get("imageUrl") or p.get("image") or ""
                items.append(ScrapedItem(
                    platform=self.platform_name, search_query=query,
                    name=name.strip(), price=price, unit=unit.strip(), image_url=image,
                ))
                if len(items) >= 5: break
            except Exception: continue
        return items
