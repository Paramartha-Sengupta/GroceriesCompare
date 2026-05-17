"""Quick probe — check page URL after nav, HTTP status, and first 500 chars of body."""
import asyncio
from playwright.async_api import async_playwright

CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
URLS = {
    "Blinkit": "https://blinkit.com/s/?q=amul%20butter",
    "BigBasket": "https://www.bigbasket.com/ps/?q=amul%20butter",
    "Zepto": "https://www.zeptonow.com/search?query=amul%20butter",
}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


async def check(name, url):
    print(f"\n{'='*60}\n{name}: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, executable_path=CHROMIUM,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = await browser.new_context(user_agent=UA, ignore_https_errors=True, viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()

        responses = {}
        page.on("response", lambda r: responses.update({r.url: r.status}) if name.lower() in r.url.lower() or "blinkit" in r.url or "bigbasket" in r.url or "zepto" in r.url else None)

        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)

            print(f"  Final URL  : {page.url}")
            print(f"  HTTP status: {resp.status if resp else 'N/A'}")
            print(f"  Title      : {await page.title()}")

            body = await page.content()
            print(f"  Body length: {len(body)} chars")
            print(f"  Body snippet:\n{body[:800]}")

            # Any visible text
            text = await page.evaluate("() => document.body ? document.body.innerText.trim().slice(0, 400) : ''")
            print(f"  Visible text: {text!r}")

        except Exception as e:
            print(f"  ERROR: {e}")
        finally:
            await browser.close()


async def main():
    for name, url in URLS.items():
        await check(name, url)

asyncio.run(main())
