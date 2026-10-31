from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.database import get_db
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(user=Depends(get_current_user)):
    db = get_db()
    products = await db.products.count_documents({})
    sales_agg = await db.sales.aggregate(
        [{"$group": {"_id": None, "units": {"$sum": "$quantity"}, "rows": {"$sum": 1}}}]
    ).to_list(1)
    units = sales_agg[0]["units"] if sales_agg else 0
    latest = await db.forecasts.find().sort("created_at", -1).to_list(50)
    upcoming = 0.0
    for fc in latest:
        for step in fc.get("forecasts") or []:
            upcoming += float(step.get("predicted_units") or 0)
    return {
        "total_products": products,
        "total_historical_units": units,
        "predicted_upcoming_demand": upcoming,
        "forecast_runs": await db.forecasts.count_documents({}),
    }


@router.get("/categories")
async def categories(user=Depends(get_current_user)):
    pipeline = [
        {
            "$lookup": {
                "from": "products",
                "localField": "product_id",
                "foreignField": "product_id",
                "as": "product",
            }
        },
        {"$unwind": "$product"},
        {"$group": {"_id": "$product.category", "units": {"$sum": "$quantity"}}},
        {"$sort": {"units": -1}},
    ]
    rows = await get_db().sales.aggregate(pipeline).to_list(50)
    return [{"category": r["_id"], "units": r["units"]} for r in rows]


@router.get("/weekly-trend")
async def weekly_trend(user=Depends(get_current_user)):
    pipeline = [
        {
            "$group": {
                "_id": {"$dateTrunc": {"date": "$date", "unit": "week", "startOfWeek": "monday"}},
                "units": {"$sum": "$quantity"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = await get_db().sales.aggregate(pipeline).to_list(500)
    return [{"week_start": r["_id"].isoformat(), "units": r["units"]} for r in rows]


@router.get("/demand-extremes")
async def demand_extremes(user=Depends(get_current_user)):
    pipeline = [
        {"$group": {"_id": "$product_id", "units": {"$sum": "$quantity"}}},
        {"$sort": {"units": -1}},
    ]
    rows = await get_db().sales.aggregate(pipeline).to_list(5000)
    high = rows[:8]
    low = list(reversed(rows[-8:])) if rows else []
    return {"high_demand": high, "low_demand": low}


@router.get("/trends")
async def google_trends(user=Depends(get_current_user)):
    rows = await get_db().trends_data.find().sort("week_start", 1).to_list(2000)
    for row in rows:
        row["id"] = str(row.pop("_id"))
    return {"available": bool(rows), "series": rows}


@router.get("/weather")
async def weather(user=Depends(get_current_user)):
    rows = await get_db().weather_data.find().sort("date", 1).to_list(2000)
    for row in rows:
        row["id"] = str(row.pop("_id"))
    return {"available": bool(rows), "series": rows, "source": "Open-Meteo (seeded) or empty until seed"}


@router.get("/festivals")
async def festivals(user=Depends(get_current_user)):
    rows = await get_db().festivals.find().sort("date", 1).to_list(2000)
    for row in rows:
        row["id"] = str(row.pop("_id"))
    return rows


@router.get("/inventory-risk")
async def inventory_risk(user=Depends(get_current_user)):
    db = get_db()
    products = await db.products.find().to_list(2000)
    inv = {i["product_id"]: i async for i in db.inventory.find()}
    cutoff = datetime.now(timezone.utc) - timedelta(days=28)
    risks = []
    for p in products:
        pid = p["product_id"]
        recent = await db.sales.aggregate(
            [
                {"$match": {"product_id": pid, "date": {"$gte": cutoff}}},
                {"$group": {"_id": None, "units": {"$sum": "$quantity"}}},
            ]
        ).to_list(1)
        weekly = (recent[0]["units"] / 4) if recent else 0
        on_hand = (inv.get(pid) or {}).get("on_hand", 0)
        fc = await db.forecasts.find_one({"product_id": pid}, sort=[("created_at", -1)])
        next_week = 0
        if fc and fc.get("forecasts"):
            next_week = float(fc["forecasts"][0].get("predicted_units") or 0)
        stockout = on_hand < next_week
        low_demand = weekly < 1
        high_demand = weekly >= 20
        unusual = abs(next_week - weekly) > max(5, 0.75 * weekly) if next_week else False
        if stockout or low_demand or high_demand or unusual:
            risks.append(
                {
                    "product_id": pid,
                    "name": p.get("name"),
                    "on_hand": on_hand,
                    "recent_weekly_avg": weekly,
                    "next_week_forecast": next_week,
                    "potential_stockout": stockout,
                    "low_demand": low_demand,
                    "high_demand": high_demand,
                    "unusual_change": unusual,
                    "note": "Forecasts are not guaranteed inventory recommendations.",
                }
            )
    return risks


@router.get("/momentum")
async def momentum(user=Depends(get_current_user)):
    pipeline = [
        {
            "$group": {
                "_id": {
                    "product_id": "$product_id",
                    "week": {"$dateTrunc": {"date": "$date", "unit": "week", "startOfWeek": "monday"}},
                },
                "units": {"$sum": "$quantity"},
            }
        },
        {"$sort": {"_id.week": 1}},
    ]
    rows = await get_db().sales.aggregate(pipeline).to_list(10000)
    by_pid = {}
    for r in rows:
        by_pid.setdefault(r["_id"]["product_id"], []).append(r["units"])
    out = []
    for pid, series in by_pid.items():
        if len(series) < 4:
            continue
        first, last = float(sum(series[:2]) / 2), float(sum(series[-2:]) / 2)
        delta = last - first
        direction = "increasing" if delta > 1 else "decreasing" if delta < -1 else "stable"
        out.append({"product_id": pid, "delta": delta, "direction": direction})
    out.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return out[:40]
