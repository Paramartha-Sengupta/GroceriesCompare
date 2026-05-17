import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from matcher import normalize_grocery_list, build_price_matrix
from optimizer import optimize, OptimizationResult
from scrapers import ALL_SCRAPERS
from scrapers.base import ScrapedItem

jobs: dict[str, dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="GroceriesCompare API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_static_dir = os.path.join(os.path.dirname(__file__), "static")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open(os.path.join(_static_dir, "index.html")) as f:
        return f.read()


# ── Request / Response models ─────────────────────────────────────────────

class CompareRequest(BaseModel):
    grocery_list: str
    pincode: str


class ItemPrice(BaseModel):
    platform: str
    name: str
    price: float
    unit: str


class PriceRow(BaseModel):
    query: str
    prices: list[ItemPrice]
    cheapest_platform: str | None


class CartSummary(BaseModel):
    platform: str
    item_count: int
    subtotal: float
    delivery_fee: float
    total: float
    items: list[str]


class CompareResponse(BaseModel):
    job_id: str
    price_matrix: list[PriceRow]
    recommended_carts: list[CartSummary]
    single_best_cart: CartSummary | None
    total_savings: float
    savings_pct: float
    unmatched_items: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────

def _build_response(job_id: str, queries: list[str], result: OptimizationResult, price_matrix: dict) -> CompareResponse:
    price_rows: list[PriceRow] = []
    for query in queries:
        row = price_matrix[query]
        prices = [
            ItemPrice(platform=p, name=item.name, price=item.price, unit=item.unit)
            for p, item in row.items()
            if item is not None
        ]
        cheapest = min(prices, key=lambda x: x.price).platform if prices else None
        price_rows.append(PriceRow(query=query, prices=prices, cheapest_platform=cheapest))

    def cart_to_summary(cart) -> CartSummary:
        return CartSummary(
            platform=cart.platform,
            item_count=len(cart.items),
            subtotal=round(cart.subtotal, 2),
            delivery_fee=round(cart.delivery_fee, 2),
            total=round(cart.total, 2),
            items=[q for q, _ in cart.items],
        )

    return CompareResponse(
        job_id=job_id,
        price_matrix=price_rows,
        recommended_carts=[cart_to_summary(c) for c in result.recommended],
        single_best_cart=cart_to_summary(result.single_best) if result.single_best else None,
        total_savings=round(result.total_savings, 2),
        savings_pct=round(result.savings_pct, 1),
        unmatched_items=result.unmatched_items,
    )


# ── Routes ────────────────────────────────────────────────────────────────

@app.post("/compare", response_model=dict)
async def start_compare(req: CompareRequest):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "result": None, "progress": {}}
    asyncio.create_task(_run_comparison(job_id, req.grocery_list, req.pincode))
    return {"job_id": job_id}


@app.get("/compare/{job_id}", response_model=dict)
async def get_result(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return {"error": "Job not found"}
    if job["status"] != "done":
        return {"status": job["status"], "progress": job["progress"]}
    return {"status": "done", "result": job["result"]}


@app.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()
    try:
        while True:
            job = jobs.get(job_id)
            if not job:
                await websocket.send_json({"event": "error", "message": "Job not found"})
                break
            await websocket.send_json({
                "event": "progress",
                "status": job["status"],
                "progress": job["progress"],
            })
            if job["status"] == "done":
                await websocket.send_json({"event": "done", "result": job["result"]})
                break
            if job["status"] == "failed":
                await websocket.send_json({"event": "failed"})
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


# ── Background task ───────────────────────────────────────────────────────

async def _run_comparison(job_id: str, grocery_list: str, pincode: str):
    job = jobs[job_id]
    job["status"] = "normalizing"
    try:
        queries = await normalize_grocery_list(grocery_list)
        job["progress"]["queries"] = queries
        job["status"] = "scraping"

        all_results: dict[str, list] = {}

        async def scrape_platform(scraper_cls):
            scraper = scraper_cls()
            name = scraper.platform_name
            job["progress"][name] = "scraping"
            try:
                results = await scraper.scrape(queries, pincode)
                all_results[name] = results
                job["progress"][name] = "done"
            except Exception as e:
                all_results[name] = []
                job["progress"][name] = f"error: {str(e)[:60]}"

        await asyncio.gather(*[scrape_platform(cls) for cls in ALL_SCRAPERS])

        job["status"] = "matching"
        price_matrix = build_price_matrix(queries, all_results)

        job["status"] = "optimizing"
        result = optimize(price_matrix)

        response = _build_response(job_id, queries, result, price_matrix)
        job["result"] = response.model_dump()
        job["status"] = "done"

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
