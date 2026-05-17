# GroceriesCompare

Compare grocery prices across Blinkit, Zepto, BigBasket, Instamart, AmazonFresh, and Flipkart Minutes. Finds the cheapest combination of apps for your full cart.

## Architecture

```
iOS App (SwiftUI)  ←→  FastAPI Backend  ←→  Playwright Scrapers  ←→  6 Platforms
```

## Repo structure

```
backend/        Python FastAPI + Playwright scrapers
ios/            SwiftUI Xcode project
```

## Backend setup

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # add your ANTHROPIC_API_KEY
uvicorn main:app --reload
```

## iOS setup

Open `ios/GroceriesCompare/` in Xcode. Set the `api_base_url` in UserDefaults or update `APIService.swift` to point to your backend URL.

## Deploy backend to Railway

1. Push this repo to GitHub
2. Create new Railway project → connect repo → set root to `backend/`
3. Add env var: `ANTHROPIC_API_KEY`
4. Deploy — Railway auto-detects `railway.json`

## How it works

1. User types grocery list + pincode in the iOS app
2. Backend normalizes the list via Claude Haiku
3. 6 Playwright scrapers run in parallel, one per platform
4. Claude Haiku matches scraped items to the search queries
5. Optimizer finds the cheapest cart split (greedy, delivery-fee-aware)
6. iOS app shows savings and recommended split
