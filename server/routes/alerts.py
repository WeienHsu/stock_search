from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.routes import USER_ID
from src.data.ticker_utils import normalize_ticker
from src.repositories.alert_repo import (
    create_price_alert,
    delete_alert,
    get_alert,
    list_alerts,
    list_events,
    set_alert_enabled,
)

router = APIRouter(tags=["alerts"])


class AlertCreate(BaseModel):
    ticker: str
    direction: str  # "above" | "below"
    threshold: float
    expires_at: float | None = None


class AlertPatch(BaseModel):
    enabled: bool


@router.get("/alerts")
def get_alerts() -> list[dict]:
    return list_alerts(USER_ID)


@router.post("/alerts")
def post_alert(body: AlertCreate) -> dict:
    if body.direction not in {"above", "below"}:
        raise HTTPException(status_code=400, detail="direction must be 'above' or 'below'")
    return create_price_alert(
        USER_ID,
        normalize_ticker(body.ticker),
        body.direction,  # type: ignore[arg-type]
        body.threshold,
        expires_at=body.expires_at,
    )


@router.patch("/alerts/{alert_id}")
def patch_alert(alert_id: str, body: AlertPatch) -> dict:
    if get_alert(alert_id) is None:
        raise HTTPException(status_code=404, detail="alert not found")
    set_alert_enabled(alert_id, body.enabled)
    return {"ok": True}


@router.delete("/alerts/{alert_id}")
def remove_alert(alert_id: str) -> dict:
    delete_alert(alert_id)
    return {"ok": True}


@router.get("/alerts/events")
def alert_events(limit: int = 50) -> list[dict]:
    return list_events(USER_ID, limit=limit)
