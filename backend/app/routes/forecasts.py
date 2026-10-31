from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.middleware.auth import get_current_user, require_roles
from app.ml.predictor import forecast_service

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])


class ForecastRequest(BaseModel):
    product_id: str | None = None
    product_ids: list[str] | None = None
    horizon_weeks: int = Field(default=4, ge=1, le=12)


async def _history(db, product_id: str) -> list[dict]:
    rows = await db.sales.find({"product_id": product_id}).sort("date", 1).to_list(5000)
    return [{"date": r["date"], "quantity": r["quantity"]} for r in rows]


async def _weather(db) -> dict:
    doc = await db.weather_data.find_one(sort=[("date", -1)])
    if not doc:
        return {}
    return {
        "temperature": doc.get("temperature"),
        "rainfall": doc.get("rainfall"),
        "humidity": doc.get("humidity"),
    }


@router.post("/predict")
async def predict(body: ForecastRequest, user=Depends(require_roles("admin", "analyst"))):
    if not forecast_service.available:
        raise HTTPException(503, f"Model not available: {forecast_service.status}")
    ids = body.product_ids or ([body.product_id] if body.product_id else [])
    if not ids:
        raise HTTPException(400, "Provide product_id or product_ids")
    db = get_db()
    weather = await _weather(db)
    results = []
    for pid in ids:
        product = await db.products.find_one({"product_id": pid})
        if not product:
            raise HTTPException(404, f"Product not found: {pid}")
        history = await _history(db, pid)
        trend = await db.trends_data.find_one({"keyword": product.get("category")}, sort=[("week_start", -1)])
        payload = forecast_service.predict_product(
            product,
            history,
            horizon_weeks=body.horizon_weeks,
            weather=weather,
            google_trend=(trend or {}).get("interest") or 0,
        )
        rec = {
            **payload,
            "created_at": datetime.now(timezone.utc),
            "created_by": user["email"],
        }
        await db.forecasts.insert_one({k: v for k, v in rec.items() if k != "_id"})
        rec.pop("_id", None)
        results.append(payload)
    return {"results": results}


@router.get("")
async def list_forecasts(product_id: str | None = None, user=Depends(get_current_user)):
    query = {"product_id": product_id} if product_id else {}
    rows = await get_db().forecasts.find(query).sort("created_at", -1).to_list(200)
    for row in rows:
        row["id"] = str(row.pop("_id"))
    return rows


@router.get("/compare/{product_id}")
async def compare(product_id: str, user=Depends(get_current_user)):
    db = get_db()
    sales = await db.sales.find({"product_id": product_id}).sort("date", 1).to_list(5000)
    latest = await db.forecasts.find_one({"product_id": product_id}, sort=[("created_at", -1)])
    return {
        "history": [
            {"date": s["date"].isoformat() if hasattr(s["date"], "isoformat") else str(s["date"]), "quantity": s["quantity"]}
            for s in sales
        ],
        "forecast": latest,
    }
