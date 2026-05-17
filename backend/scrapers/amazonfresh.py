import re
import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper, ScrapeResult, ScrapedItem, DESKTOP_UA

FRESH_NODE = "5940050031"


class AmazonFreshScraper(BaseScraper):
    platform_name = "AmazonFresh"

    async def _scrape_query(self, client: httpx.AsyncClient, query: str, lat: float, lon: float) -> ScrapeResult:
        headers = {
            "User-Agent": DESKTOP_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
        try:
            r = await client.get(
                "https://www.amazon.in/s",
                params={"k": query, "i": "grocery", "rh": f"n:{FRESH_NODE}"},
                headers=headers,
                timeout=20,
            )
            r.raise_for_status()
            return ScrapeResult(
                platform=self.platform_name, query=query,
                items=self._parse_html(query, r.text)
            )
        except Exception as e:
            return ScrapeResult(platform=self.platform_name, query=query, error=str(e))

    def _parse_html(self, query: str, html: str) -> list[ScrapedItem]:
        items = []
        try:
            soup = BeautifulSoup(html, "lxml")
            cards = soup.select("div[data-component-type='s-search-result']")
            for card in cards[:5]:
                try:
                    name_el = card.select_one("h2 span, h2 a span")
                    if not name_el: continue
                    name = name_el.get_text(strip=True)
                    whole_el = card.select_one(".a-price-whole")
                    if not whole_el: continue
                    whole = re.sub(r"[^0-9]", "", whole_el.get_text())
                    frac_el = card.select_one(".a-price-fraction")
                    frac = frac_el.get_text(strip=True) if frac_el else "0"
                    price = float(f"{whole}.{frac}") if whole else 0
                    if price == 0: continue
                    unit_el = card.select_one(".a-size-base.a-color-secondary")
                    unit = unit_el.get_text(strip=True) if unit_el else ""
                    img_el = card.select_one("img.s-image")
                    image = img_el.get("src", "") if img_el else ""
                    items.append(ScrapedItem(
                        platform=self.platform_name, search_query=query,
                        name=name, price=price, unit=unit, image_url=image,
                    ))
                except Exception: continue
        except Exception: pass
        return items
