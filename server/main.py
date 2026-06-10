"""Stock Intelligence API — thin FastAPI layer over src/ core.

Run: uvicorn server.main:app --reload --port 8700
"""

from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importing strategy modules registers them in the strategy registry.
import src.strategies.strategy_d  # noqa: F401
import src.strategies.strategy_kd  # noqa: F401
import src.strategies.bias_strategy  # noqa: F401

from server.routes import alerts, chip, inbox, kline, market, quotes, scan, watchlist

app = FastAPI(title="Stock Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (quotes.router, kline.router, watchlist.router, alerts.router, scan.router, market.router, inbox.router, chip.router):
    app.include_router(router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# Serve the built frontend (web/dist) in production; in dev, Vite proxies /api.
_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="web")
