import json
import os
import re
import anthropic
from scrapers.base import ScrapedItem

_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
_client = anthropic.Anthropic(api_key=_api_key) if _api_key else None


async def normalize_grocery_list(raw_input: str) -> list[str]:
    """Convert free-text grocery list into clean search queries."""
    if _client:
        try:
            message = _client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Convert this grocery list into clean search queries for Indian grocery apps.\n"
                        f"Return a JSON array of strings. Each string should be a concise search query.\n"
                        f"Preserve quantities if mentioned. Keep brand names if specified.\n\n"
                        f"Input: {raw_input}\n\n"
                        f"Return only valid JSON array, no explanation."
                    )
                }]
            )
            text = message.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception:
            pass

    # Fallback: split by comma or newline, strip quantities into search-friendly form
    parts = re.split(r"[,\n]+", raw_input)
    queries = []
    for p in parts:
        p = p.strip()
        if p:
            queries.append(p)
    return queries


def pick_best_match(query: str, candidates: list[ScrapedItem]) -> ScrapedItem | None:
    """Pick the most relevant scraped item for a search query using fuzzy + optional LLM."""
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    from thefuzz import process
    names = [c.name for c in candidates]
    best_name, score = process.extractOne(query, names)
    if score >= 75:
        return next(c for c in candidates if c.name == best_name)

    if _client:
        try:
            candidate_list = "\n".join(
                f"{i+1}. {c.name} ({c.unit}) — ₹{c.price}" for i, c in enumerate(candidates)
            )
            message = _client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=64,
                messages=[{
                    "role": "user",
                    "content": (
                        f"User searched for: '{query}'\n"
                        f"Which product best matches? Reply with just the number.\n\n"
                        f"{candidate_list}"
                    )
                }]
            )
            idx = int(message.content[0].text.strip()) - 1
            return candidates[idx]
        except Exception:
            pass

    # Final fallback: return fuzzy best regardless of score
    return next(c for c in candidates if c.name == best_name)


def build_price_matrix(
    queries: list[str],
    all_results: dict[str, list],
) -> dict[str, dict[str, ScrapedItem | None]]:
    """Returns: { query: { platform: best_matching_ScrapedItem | None } }"""
    platforms = list(all_results.keys())
    matrix: dict[str, dict[str, ScrapedItem | None]] = {}
    for query in queries:
        matrix[query] = {}
        for platform in platforms:
            candidates = [
                item
                for result in all_results[platform]
                if result.query == query
                for item in result.items
            ]
            matrix[query][platform] = pick_best_match(query, candidates)
    return matrix

