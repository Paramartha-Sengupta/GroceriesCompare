from .blinkit import BlinkitScraper
from .zepto import ZeptoScraper
from .bigbasket import BigBasketScraper
from .instamart import InstamartScraper
from .amazonfresh import AmazonFreshScraper
from .flipkart_minutes import FlipkartMinutesScraper

ALL_SCRAPERS = [
    BlinkitScraper,
    ZeptoScraper,
    BigBasketScraper,
    InstamartScraper,
    AmazonFreshScraper,
    FlipkartMinutesScraper,
]
