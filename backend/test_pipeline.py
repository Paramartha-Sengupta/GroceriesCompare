"""
End-to-end pipeline test using realistic mock scrape data.
Tests: item matching, price matrix construction, cart optimization.
Run: python3 test_pipeline.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from scrapers.base import ScrapedItem, ScrapeResult
from matcher import build_price_matrix
from optimizer import optimize

# ── Realistic mock scrape data ────────────────────────────────────────────────
# Simulates what each platform returns for a 5-item grocery list

MOCK_RESULTS: dict[str, list[ScrapeResult]] = {
    # Blinkit cheaper on: butter, eggs, bread, atta  (subtotal > ₹199 → free delivery)
    "Blinkit": [
        ScrapeResult("Blinkit", "amul butter 500g", [
            ScrapedItem("Blinkit", "amul butter 500g", "Amul Butter - Pasteurised, 500 g", 249.0, "500 g"),
        ]),
        ScrapeResult("Blinkit", "eggs 12", [
            ScrapedItem("Blinkit", "eggs 12", "Farm Fresh White Eggs, 12 pcs", 87.0, "12 pcs"),
        ]),
        ScrapeResult("Blinkit", "bread", [
            ScrapedItem("Blinkit", "bread", "Harvest Gold White Bread, 400 g", 36.0, "400 g"),
        ]),
        ScrapeResult("Blinkit", "atta 5kg", [
            ScrapedItem("Blinkit", "atta 5kg", "Aashirvaad Atta 5 kg", 258.0, "5 kg"),
        ]),
        ScrapeResult("Blinkit", "2 litre milk", [
            ScrapedItem("Blinkit", "2 litre milk", "Amul Gold Full Cream Milk, 2 L", 122.0, "2 L"),
        ]),
        ScrapeResult("Blinkit", "tomatoes 1kg", [
            ScrapedItem("Blinkit", "tomatoes 1kg", "Fresh Tomatoes, 1 kg", 55.0, "1 kg"),
        ]),
        ScrapeResult("Blinkit", "sugar 1kg", [
            ScrapedItem("Blinkit", "sugar 1kg", "India Gate Sugar, 1 kg", 52.0, "1 kg"),
        ]),
        ScrapeResult("Blinkit", "onions 2kg", [
            ScrapedItem("Blinkit", "onions 2kg", "Fresh Onions, 2 kg", 68.0, "2 kg"),
        ]),
    ],
    # Zepto cheaper on: milk, tomatoes, sugar, onions  (subtotal > ₹149 → free delivery)
    "Zepto": [
        ScrapeResult("Zepto", "amul butter 500g", [
            ScrapedItem("Zepto", "amul butter 500g", "Amul Butter Pasteurised 500g", 265.0, "500g"),
        ]),
        ScrapeResult("Zepto", "eggs 12", [
            ScrapedItem("Zepto", "eggs 12", "Fresho Eggs White Large, 12 Pcs", 96.0, "12 pcs"),
        ]),
        ScrapeResult("Zepto", "bread", [
            ScrapedItem("Zepto", "bread", "Modern White Bread 400g", 44.0, "400 g"),
        ]),
        ScrapeResult("Zepto", "atta 5kg", [
            ScrapedItem("Zepto", "atta 5kg", "Aashirvaad Atta 5kg", 275.0, "5 kg"),
        ]),
        ScrapeResult("Zepto", "2 litre milk", [
            ScrapedItem("Zepto", "2 litre milk", "Heritage Fresh Cow Milk, 2 L", 104.0, "2 L"),
        ]),
        ScrapeResult("Zepto", "tomatoes 1kg", [
            ScrapedItem("Zepto", "tomatoes 1kg", "Tomato 1 kg", 38.0, "1 kg"),
        ]),
        ScrapeResult("Zepto", "sugar 1kg", [
            ScrapedItem("Zepto", "sugar 1kg", "Sugar 1kg", 45.0, "1 kg"),
        ]),
        ScrapeResult("Zepto", "onions 2kg", [
            ScrapedItem("Zepto", "onions 2kg", "Onion 2 kg", 52.0, "2 kg"),
        ]),
    ],
    "BigBasket": [
        ScrapeResult("BigBasket", "amul butter 500g", [
            ScrapedItem("BigBasket", "amul butter 500g", "Amul - Butter, Pasteurised, 500 gm", 268.0, "500 gm"),
        ]),
        ScrapeResult("BigBasket", "eggs 12", [
            ScrapedItem("BigBasket", "eggs 12", "Fresho Eggs - White, Large, 12 pcs", 93.0, "12 pcs"),
        ]),
        ScrapeResult("BigBasket", "bread", [
            ScrapedItem("BigBasket", "bread", "Harvest Gold Premium Bread, 400 g", 42.0, "400 g"),
        ]),
        ScrapeResult("BigBasket", "atta 5kg", [
            ScrapedItem("BigBasket", "atta 5kg", "Aashirvaad Atta 5kg", 262.0, "5 kg"),
        ]),
        ScrapeResult("BigBasket", "2 litre milk", [
            ScrapedItem("BigBasket", "2 litre milk", "Nandini Toned Milk, 2 ltr", 110.0, "2 ltr"),
        ]),
        ScrapeResult("BigBasket", "tomatoes 1kg", [
            ScrapedItem("BigBasket", "tomatoes 1kg", "Fresho Tomato, 1 kg", 42.0, "1 kg"),
        ]),
        ScrapeResult("BigBasket", "sugar 1kg", [
            ScrapedItem("BigBasket", "sugar 1kg", "BB Royal Sugar, 1 kg", 48.0, "1 kg"),
        ]),
        ScrapeResult("BigBasket", "onions 2kg", [
            ScrapedItem("BigBasket", "onions 2kg", "Fresho Onion, 2 kg", 60.0, "2 kg"),
        ]),
    ],
}

QUERIES = ["amul butter 500g", "eggs 12", "bread", "atta 5kg", "2 litre milk", "tomatoes 1kg", "sugar 1kg", "onions 2kg"]


def separator(title=""):
    print(f"\n{'─'*60}")
    if title:
        print(f"  {title}")
        print(f"{'─'*60}")


def test_price_matrix():
    separator("PRICE MATRIX")
    matrix = build_price_matrix(QUERIES, MOCK_RESULTS)

    platforms = list(MOCK_RESULTS.keys())
    header = f"{'Item':<22}" + "".join(f"{p:<16}" for p in platforms)
    print(header)
    print("-" * (22 + 16 * len(platforms)))

    for query in QUERIES:
        row = f"{query:<22}"
        prices = []
        for p in platforms:
            item = matrix[query].get(p)
            if item:
                row += f"₹{item.price:<15.0f}"
                prices.append(item.price)
            else:
                row += f"{'—':<16}"
        print(row)

    return matrix


def test_optimizer(matrix):
    separator("OPTIMIZATION RESULT")
    result = optimize(matrix)

    print(f"\n{'RECOMMENDED CART SPLIT':}")
    total_recommended = 0
    for cart in result.recommended:
        print(f"\n  📦 {cart.platform}")
        for q, item in cart.items:
            print(f"     • {q:<22} → {item.name[:35]:<35}  ₹{item.price:.0f}")
        print(f"     Subtotal: ₹{cart.subtotal:.0f}  +  Delivery: ₹{cart.delivery_fee:.0f}  =  ₹{cart.total:.0f}")
        total_recommended += cart.total

    separator()
    print(f"  Recommended total  : ₹{total_recommended:.0f}")

    if result.single_best:
        sc = result.single_best
        print(f"  Single-app baseline: ₹{sc.total:.0f}  ({sc.platform})")

    if result.total_savings > 0:
        print(f"\n  ✅ You SAVE ₹{result.total_savings:.0f} ({result.savings_pct:.1f}%)")
    else:
        print(f"\n  ℹ️  Single app is already cheapest — no split needed")

    if result.unmatched_items:
        print(f"\n  ⚠️  Unmatched items: {result.unmatched_items}")


if __name__ == "__main__":
    print("\n🛒  GroceriesCompare — Pipeline Test")
    print(f"Items: {QUERIES}")
    print(f"Platforms: {list(MOCK_RESULTS.keys())}")

    matrix = test_price_matrix()
    test_optimizer(matrix)
    print("\n✓ Pipeline test complete\n")
