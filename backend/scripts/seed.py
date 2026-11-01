"""Seed MongoDB from processed ML tables (requires MONGODB_URI)."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import certifi
import pandas as pd
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env")

PROCESSED = ROOT / "ml" / "datasets" / "processed"


async def seed():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    name = os.getenv("DATABASE_NAME", "fashion_forecasting")
    if "YOUR_MONGODB" in uri:
        raise SystemExit("Set MONGODB_URI first")
    client = AsyncIOMotorClient(uri, tlsCAFile=certifi.where())
    db = client[name]

    products = pd.read_csv(PROCESSED / "products.csv")
    mapping = pd.read_csv(PROCESSED / "product_sales_map.csv") if (PROCESSED / "product_sales_map.csv").exists() else None
    hist = set()
    if mapping is not None:
        hist = set(mapping.loc[mapping["has_history"], "product_id"])

    await db.products.delete_many({"seed": True})
    docs = []
    for row in products.itertuples(index=False):
        docs.append(
            {
                "product_id": row.product_id,
                "name": f"{row.category} {row.product_id[-8:]}",
                "category": row.category,
                "colour": row.colour,
                "pattern": row.pattern,
                "sleeve_type": row.sleeve_type,
                "description": f"Catalog item from clothing-dataset-small ({row.category}).",
                "image_url": f"/catalog-images/{Path(row.image_path).name}",
                "image_path": row.image_path,
                "has_history": row.product_id in hist,
                "seed": True,
                "created_at": datetime.now(timezone.utc),
            }
        )
    if docs:
        await db.products.insert_many(docs)

    panel_path = PROCESSED / "panel.parquet"
    if panel_path.exists():
        panel = pd.read_parquet(panel_path)
        await db.sales.delete_many({"source": "seed"})
        sales_docs = []
        # keep payload reasonable
        sample_ids = list(panel["product_id"].unique()[:80])
        sub = panel[panel["product_id"].isin(sample_ids)]
        for row in sub.itertuples(index=False):
            sales_docs.append(
                {
                    "product_id": row.product_id,
                    "date": pd.to_datetime(row.week_start).to_pydatetime(),
                    "quantity": float(row.units),
                    "source": "seed",
                    "created_at": datetime.now(timezone.utc),
                }
            )
        if sales_docs:
            await db.sales.insert_many(sales_docs)

    weather_path = PROCESSED / "weather_daily.csv"
    if weather_path.exists():
        weather = pd.read_csv(weather_path, parse_dates=["date"])
        await db.weather_data.delete_many({})
        await db.weather_data.insert_many(
            [
                {
                    "date": pd.to_datetime(r.date).to_pydatetime(),
                    "temperature": r.temperature,
                    "rainfall": r.rainfall,
                    "humidity": None if pd.isna(r.humidity) else r.humidity,
                    "location": "London",
                }
                for r in weather.itertuples(index=False)
            ]
        )

    fest_path = PROCESSED / "festivals.csv"
    if fest_path.exists():
        fest = pd.read_csv(fest_path, parse_dates=["date"])
        await db.festivals.delete_many({})
        rows = []
        for r in fest.itertuples(index=False):
            if bool(r.is_holiday):
                rows.append({"date": pd.to_datetime(r.date).to_pydatetime(), "name": r.holiday_name, "region": "GB"})
        if rows:
            await db.festivals.insert_many(rows)

    trends_path = PROCESSED / "google_trends.csv"
    if trends_path.exists():
        trends = pd.read_csv(trends_path)
        date_col = "week_start" if "week_start" in trends.columns else trends.columns[0]
        await db.trends_data.delete_many({})
        tdocs = []
        for _, row in trends.iterrows():
            week = pd.to_datetime(row[date_col]).to_pydatetime()
            for col in trends.columns:
                if col in {date_col, "week_start", "isPartial"}:
                    continue
                val = row[col]
                if pd.isna(val):
                    continue
                tdocs.append({"keyword": col, "week_start": week, "interest": float(val)})
        if tdocs:
            await db.trends_data.insert_many(tdocs)

    metrics_path = ROOT / "ml" / "models" / "evaluation_metrics.json"
    if metrics_path.exists():
        import json

        metrics = json.loads(metrics_path.read_text())
        await db.model_metrics.delete_many({"model_version": metrics.get("model_version")})
        await db.model_metrics.insert_one({**metrics, "ingested_at": datetime.now(timezone.utc)})

    if panel_path.exists():
        panel = pd.read_parquet(panel_path)
        recent = panel.groupby("product_id")["units"].mean()
        await db.inventory.delete_many({"seed": True})
        inv_docs = []
        for pid, avg in recent.items():
            inv_docs.append(
                {
                    "product_id": pid,
                    "on_hand": float(max(0, round(avg * 2))),
                    "reorder_point": float(max(5, round(avg))),
                    "seed": True,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
        if inv_docs:
            await db.inventory.insert_many(inv_docs)

    sys.path.insert(0, str(ROOT / "backend"))
    from app.utils.security import hash_password

    demo_email = "demo@atelier.local"
    if not await db.users.find_one({"email": demo_email}):
        await db.users.insert_one(
            {
                "name": "Demo Analyst",
                "email": demo_email,
                "password_hash": hash_password("college123"),
                "role": "admin",
                "created_at": datetime.now(timezone.utc),
            }
        )

    print("Seed complete")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
