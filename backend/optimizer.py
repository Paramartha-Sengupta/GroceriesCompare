from dataclasses import dataclass
from scrapers.base import ScrapedItem

DELIVERY_FEES: dict[str, dict] = {
    "Blinkit":          {"free_above": 199,  "fee": 25},
    "Zepto":            {"free_above": 149,  "fee": 25},
    "BigBasket":        {"free_above": 600,  "fee": 40},
    "Instamart":        {"free_above": 199,  "fee": 30},
    "AmazonFresh":      {"free_above": 300,  "fee": 40},
    "Flipkart Minutes": {"free_above": 199,  "fee": 25},
}


@dataclass
class CartOption:
    platform: str
    items: list[tuple[str, ScrapedItem]]  # (query, item)
    subtotal: float
    delivery_fee: float

    @property
    def total(self) -> float:
        return self.subtotal + self.delivery_fee


@dataclass
class OptimizationResult:
    recommended: list[CartOption]       # best split across platforms
    single_best: CartOption             # cheapest single-platform option
    total_savings: float
    savings_pct: float
    unmatched_items: list[str]


def _delivery_fee(platform: str, subtotal: float) -> float:
    config = DELIVERY_FEES.get(platform, {"free_above": 0, "fee": 0})
    return 0.0 if subtotal >= config["free_above"] else config["fee"]


def optimize(
    price_matrix: dict[str, dict[str, ScrapedItem | None]]
) -> OptimizationResult:
    """
    Greedy optimizer: for each item pick the cheapest platform.
    Then consolidate into carts, applying delivery fees.
    Also computes the single-cheapest-platform baseline.
    """
    queries = list(price_matrix.keys())
    platforms = list(next(iter(price_matrix.values())).keys())

    unmatched: list[str] = [q for q in queries if all(v is None for v in price_matrix[q].values())]
    matched_queries = [q for q in queries if q not in unmatched]

    # --- Single-platform totals ---
    platform_totals: dict[str, float] = {}
    platform_items: dict[str, list[tuple[str, ScrapedItem]]] = {p: [] for p in platforms}

    for platform in platforms:
        subtotal = 0.0
        for q in matched_queries:
            item = price_matrix[q].get(platform)
            if item:
                subtotal += item.price
                platform_items[platform].append((q, item))
        platform_totals[platform] = subtotal

    valid_platforms = [p for p in platforms if platform_items[p]]
    if not valid_platforms:
        return OptimizationResult([], None, 0.0, 0.0, unmatched)

    best_platform = min(valid_platforms, key=lambda p: platform_totals[p] + _delivery_fee(p, platform_totals[p]))
    best_subtotal = platform_totals[best_platform]
    single_best = CartOption(
        platform=best_platform,
        items=platform_items[best_platform],
        subtotal=best_subtotal,
        delivery_fee=_delivery_fee(best_platform, best_subtotal),
    )

    # --- Greedy split ---
    # Assign each item to the cheapest platform that has it
    assignment: dict[str, str] = {}
    for q in matched_queries:
        available = {p: price_matrix[q][p] for p in platforms if price_matrix[q][p] is not None}
        if available:
            assignment[q] = min(available, key=lambda p: available[p].price)

    # Group by platform
    split_carts: dict[str, list[tuple[str, ScrapedItem]]] = {}
    for q, platform in assignment.items():
        split_carts.setdefault(platform, []).append((q, price_matrix[q][platform]))

    cart_options: list[CartOption] = []
    for platform, items in split_carts.items():
        subtotal = sum(item.price for _, item in items)
        cart_options.append(CartOption(
            platform=platform,
            items=items,
            subtotal=subtotal,
            delivery_fee=_delivery_fee(platform, subtotal),
        ))

    split_total = sum(c.total for c in cart_options)
    single_total = single_best.total
    savings = single_total - split_total
    savings_pct = (savings / single_total * 100) if single_total > 0 else 0.0

    # Only recommend split if it actually saves money
    recommended = cart_options if savings > 0 else [single_best]

    return OptimizationResult(
        recommended=recommended,
        single_best=single_best,
        total_savings=max(savings, 0.0),
        savings_pct=max(savings_pct, 0.0),
        unmatched_items=unmatched,
    )
