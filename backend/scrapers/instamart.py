import httpx
from .base import BaseScraper, ScrapeResult, ScrapedItem, MOBILE_UA


class InstamartScraper(BaseScraper):
    platform_name = "Instamart"

    async def _scrape_query(self, client: httpx.AsyncClient, query: str, lat: float, lon: float) -> ScrapeResult:
        headers = {
            "User-Agent": MOBILE_UA,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://www.swiggy.com",
            "Referer": f"https://www.swiggy.com/instamart/search?query={query}",
        }
        try:
            r = await client.get(
                "https://www.swiggy.com/api/instamart/search",
                params={
                    "pageNumber": 0,
                    "searchResultsOffset": 0,
                    "limit": 15,
                    "query": query,
                    "ageConsent": "false",
                    "layoutId": 3994,
                    "pageType": "INSTAMART_SEARCH_PAGE",
                    "isPreSearchTag": "false",
                    "highConfidencePageNo": 0,
                    "lowConfidencePageNo": 0,
                },
                headers=headers,
                timeout=15,
            )
            r.raise_for_status()
            body = r.json()
            products = []
            if isinstance(body, dict):
                widgets = (body.get("data", {}).get("widgets") or body.get("widgets") or [])
                for w in widgets:
                    prods = w.get("data", {}).get("products") or w.get("products") or []
                    products.extend(prods)
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
                name = p.get("name") or p.get("display_name") or ""
                if not name or name in seen: continue
                seen.add(name)
                price = float(p.get("price") or p.get("instamart_price") or p.get("mrp") or 0)
                if price > 5000: price /= 100
                unit = str(p.get("quantity") or p.get("unit") or p.get("weight") or "")
                image = p.get("image_id") or p.get("image") or ""
                items.append(ScrapedItem(
                    platform=self.platform_name, search_query=query,
                    name=name.strip(), price=price, unit=unit.strip(), image_url=image,
                ))
                if len(items) >= 5: break
            except Exception: continue
        return items
