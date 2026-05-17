import httpx
from .base import BaseScraper, ScrapeResult, ScrapedItem, DESKTOP_UA


class BigBasketScraper(BaseScraper):
    platform_name = "BigBasket"

    async def _scrape_query(self, client: httpx.AsyncClient, query: str, lat: float, lon: float) -> ScrapeResult:
        headers = {
            "User-Agent": DESKTOP_UA,
            "Accept": "application/json, text/plain, */*",
            "x-channel": "web",
            "Referer": "https://www.bigbasket.com/",
            "Origin": "https://www.bigbasket.com",
        }
        try:
            r = await client.get(
                "https://www.bigbasket.com/listing-svc/v2/products/",
                params={
                    "type": "ps",
                    "q": query,
                    "tab_type": '["prd"]',
                    "sorted_on": "relevance",
                    "listtype": "ps",
                },
                headers=headers,
                timeout=15,
            )
            r.raise_for_status()
            body = r.json()
            products = []
            if isinstance(body, dict):
                for tab in (body.get("tab_info") or [body]):
                    prods = tab.get("prod_list") or []
                    if prods:
                        products = prods; break
                if not products:
                    for key in ("products", "data", "items"):
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
                name = p.get("desc") or p.get("name") or p.get("product_name") or ""
                if not name or name in seen: continue
                seen.add(name)
                pricing = p.get("pricing") or {}
                disc = (pricing.get("discount") or {})
                price = float(disc.get("dsc_prc") or pricing.get("np") or
                              p.get("sp") or p.get("price") or p.get("mrp") or 0)
                unit = str(p.get("w") or p.get("unit") or p.get("qty") or "")
                image = (p.get("images") or [{}])[0].get("s") or p.get("image") or ""
                items.append(ScrapedItem(
                    platform=self.platform_name, search_query=query,
                    name=name.strip(), price=price, unit=unit.strip(), image_url=image,
                ))
                if len(items) >= 5: break
            except Exception: continue
        return items
