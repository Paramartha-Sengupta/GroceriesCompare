"""
Probe script — loads search pages for Blinkit, BigBasket, Zepto
and dumps what product-related elements are actually in the DOM.
Run: python3 probe.py
"""
import asyncio
import json
from playwright.async_api import async_playwright

CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
PINCODE = "500032"
QUERY = "amul butter"

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

PLATFORMS = {
    "Blinkit": {
        "search_url": f"https://blinkit.com/s/?q={QUERY.replace(' ', '%20')}",
        "price_selectors": [
            "[class*='Price__StyledPrice']",
            "[class*='price']",
            ".product-price",
            "[data-testid*='price']",
        ],
        "name_selectors": [
            "[class*='Product__name']",
            "[class*='ProductName']",
            "[class*='product-name']",
            "div[class*='plp'] h3",
        ],
    },
    "BigBasket": {
        "search_url": f"https://www.bigbasket.com/ps/?q={QUERY.replace(' ', '%20')}",
        "price_selectors": [
            "[class*='discnt-price']",
            "[class*='sp--']",
            "span[class*='Price']",
            "[class*='price']",
        ],
        "name_selectors": [
            "[class*='prod-name']",
            "a[class*='prod-name']",
            "[class*='SKUDes']",
        ],
    },
    "Zepto": {
        "search_url": f"https://www.zeptonow.com/search?query={QUERY.replace(' ', '%20')}",
        "price_selectors": [
            "[class*='price']",
            "[class*='Price']",
            "span[data-testid*='price']",
        ],
        "name_selectors": [
            "h5[class*='font-semibold']",
            "[class*='productName']",
            "[data-testid*='name']",
        ],
    },
}


async def probe_platform(name: str, config: dict):
    print(f"\n{'='*60}")
    print(f"PROBING: {name}")
    print(f"URL: {config['search_url']}")
    print('='*60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=DESKTOP_UA,
            viewport={"width": 1280, "height": 900},
            extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        try:
            await page.goto(config["search_url"], wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)

            title = await page.title()
            print(f"Page title: {title}")

            # Try each name selector
            print("\n--- NAME SELECTORS ---")
            for sel in config["name_selectors"]:
                els = page.locator(sel)
                count = await els.count()
                if count > 0:
                    try:
                        text = await els.first.inner_text(timeout=2000)
                        print(f"  ✓ '{sel}' → {count} hits | first: {text[:60]!r}")
                    except Exception:
                        print(f"  ✓ '{sel}' → {count} hits (text read failed)")
                else:
                    print(f"  ✗ '{sel}' → 0 hits")

            # Try each price selector
            print("\n--- PRICE SELECTORS ---")
            for sel in config["price_selectors"]:
                els = page.locator(sel)
                count = await els.count()
                if count > 0:
                    try:
                        text = await els.first.inner_text(timeout=2000)
                        print(f"  ✓ '{sel}' → {count} hits | first: {text[:40]!r}")
                    except Exception:
                        print(f"  ✓ '{sel}' → {count} hits (text read failed)")
                else:
                    print(f"  ✗ '{sel}' → 0 hits")

            # Dump interesting class names from the DOM
            print("\n--- DOM SNAPSHOT (classes with 'price' or 'product') ---")
            classes = await page.evaluate("""() => {
                const all = document.querySelectorAll('*');
                const seen = new Set();
                all.forEach(el => {
                    el.className.toString().split(' ').forEach(c => {
                        if (c && (c.toLowerCase().includes('price') ||
                                  c.toLowerCase().includes('product') ||
                                  c.toLowerCase().includes('item'))) {
                            seen.add(c);
                        }
                    });
                });
                return [...seen].slice(0, 40);
            }""")
            for cls in classes:
                print(f"  .{cls}")

        except Exception as e:
            print(f"ERROR: {e}")
        finally:
            await browser.close()


async def main():
    for name, config in PLATFORMS.items():
        await probe_platform(name, config)


if __name__ == "__main__":
    asyncio.run(main())
