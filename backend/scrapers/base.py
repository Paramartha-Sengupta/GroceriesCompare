import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class ScrapedItem:
    platform: str
    search_query: str
    name: str
    price: float
    unit: str
    image_url: Optional[str] = None
    in_stock: bool = True
    original_price: Optional[float] = None


@dataclass
class ScrapeResult:
    platform: str
    query: str
    items: list[ScrapedItem] = field(default_factory=list)
    error: Optional[str] = None


async def pincode_to_latlon(pincode: str) -> tuple[float, float]:
    """Convert Indian pincode to lat/lon via OpenStreetMap Nominatim."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"postalcode": pincode, "country": "India", "format": "json", "limit": 1},
                headers={"User-Agent": "GroceriesCompare/1.0 grocery-price-comparison"},
            )
            data = r.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    # Fallback: Mumbai coords
    return 19.0760, 72.8777


class BaseScraper(ABC):
    platform_name: str = ""

    async def scrape(self, queries: list[str], pincode: str) -> list[ScrapeResult]:
        lat, lon = await pincode_to_latlon(pincode)
        results = []
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": MOBILE_UA},
        ) as client:
            for query in queries:
                try:
                    result = await self._scrape_query(client, query, lat, lon)
                except Exception as e:
                    result = ScrapeResult(platform=self.platform_name, query=query, error=str(e))
                results.append(result)
        return results

    @abstractmethod
    async def _scrape_query(
        self, client: httpx.AsyncClient, query: str, lat: float, lon: float
    ) -> ScrapeResult:
        pass
