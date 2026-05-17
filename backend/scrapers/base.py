import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from playwright.async_api import async_playwright, Page

CHROMIUM_PATH = os.environ.get(
    "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
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
    original_price: Optional[float] = None  # if discounted


@dataclass
class ScrapeResult:
    platform: str
    query: str
    items: list[ScrapedItem] = field(default_factory=list)
    error: Optional[str] = None


class BaseScraper(ABC):
    platform_name: str = ""
    base_url: str = ""

    async def scrape(self, queries: list[str], pincode: str) -> list[ScrapeResult]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                executable_path=CHROMIUM_PATH,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                    "Mobile/15E148 Safari/604.1"
                ),
                viewport={"width": 390, "height": 844},
                ignore_https_errors=True,
            )
            page = await context.new_page()

            results: list[ScrapeResult] = []
            try:
                await self.set_location(page, pincode)
                for query in queries:
                    result = await self._scrape_query(page, query)
                    results.append(result)
            finally:
                await browser.close()

        return results

    @abstractmethod
    async def set_location(self, page: Page, pincode: str) -> None:
        """Set delivery pincode on the platform."""

    @abstractmethod
    async def _scrape_query(self, page: Page, query: str) -> ScrapeResult:
        """Search for one item and return top results."""
