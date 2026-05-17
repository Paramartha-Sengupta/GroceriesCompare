#!/bin/bash
# Run the GroceriesCompare backend locally for testing

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Virtual env
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

# 2. Dependencies
pip install -r requirements.txt -q

# 3. Playwright browser
python -m playwright install chromium

# 4. .env
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env — please add your ANTHROPIC_API_KEY"
  open .env 2>/dev/null || nano .env
fi
export $(grep -v '^#' .env | xargs) 2>/dev/null || true

# 5. Start server
echo ""
echo "Backend running at http://localhost:8000"
echo "Docs:            http://localhost:8000/docs"
echo ""
uvicorn main:app --reload --host 0.0.0.0 --port 8000
