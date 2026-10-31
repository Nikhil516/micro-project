"""Clean, align, and weekly-aggregate catalog + sales + covariates."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.preprocessing.paths import PROCESSED_DIR, ROOT, ensure_dirs

SEASON_MAP = {
    12: "winter",
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
}


def _week_start(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.tz_localize(None).dt.to_period("W-SUN").dt.start_time


def winsorize(s: pd.Series, p: float = 0.01) -> pd.Series:
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def align_products_to_sales(products: pd.DataFrame, weekly: pd.DataFrame) -> pd.DataFrame:
    """Map real UCI weekly series onto catalog SKUs by category (documented join)."""
    mapped_rows = []
    leftover_products = []
    for category, prod_group in products.groupby("category"):
        series_ids = (
            weekly.loc[weekly["category"] == category, "stock_code"].drop_duplicates().tolist()
        )
        prod_ids = prod_group["product_id"].tolist()
        n = min(len(series_ids), len(prod_ids))
        for i in range(n):
            mapped_rows.append(
                {
                    "product_id": prod_ids[i],
                    "stock_code": str(series_ids[i]),
                    "category": category,
                    "has_history": True,
                }
            )
        for pid in prod_ids[n:]:
            leftover_products.append(
                {
                    "product_id": pid,
                    "stock_code": None,
                    "category": category,
                    "has_history": False,
                }
            )
    mapping = pd.DataFrame(mapped_rows + leftover_products)
    return mapping


def add_calendar(frame: pd.DataFrame, date_col: str) -> pd.DataFrame:
    dt = pd.to_datetime(frame[date_col])
    frame = frame.copy()
    frame["week_number"] = dt.dt.isocalendar().week.astype(int)
    frame["month"] = dt.dt.month
    frame["year"] = dt.dt.year
    frame["season"] = frame["month"].map(SEASON_MAP)
    return frame


def preprocess() -> Path:
    ensure_dirs()
    products = pd.read_csv(PROCESSED_DIR / "products.csv")
    weekly = pd.read_csv(PROCESSED_DIR / "uci_weekly_fashion.csv", parse_dates=["week_start"])
    weekly["stock_code"] = weekly["stock_code"].astype(str)
    weather = pd.read_csv(PROCESSED_DIR / "weather_daily.csv", parse_dates=["date"])
    festivals = pd.read_csv(PROCESSED_DIR / "festivals.csv", parse_dates=["date"])

    products = products.drop_duplicates(subset=["product_id"])
    weekly = weekly.dropna(subset=["week_start", "units"])
    weekly["units"] = winsorize(weekly["units"].astype(float))

    mapping = align_products_to_sales(products, weekly)
    mapping.to_csv(PROCESSED_DIR / "product_sales_map.csv", index=False)

    hist = weekly.merge(mapping[mapping["has_history"]], on=["stock_code", "category"], how="inner")
    hist = hist.merge(products, on=["product_id", "category"], how="left")

    weather["week_start"] = _week_start(weather["date"])
    weather_w = weather.groupby("week_start", as_index=False).agg(
        temperature=("temperature", "mean"),
        rainfall=("rainfall", "sum"),
        humidity=("humidity", "mean"),
    )
    festivals["week_start"] = _week_start(festivals["date"])
    fest_w = festivals.groupby("week_start", as_index=False).agg(
        holiday_days=("is_holiday", "sum"),
    )

    panel = hist.merge(weather_w, on="week_start", how="left")
    panel = panel.merge(fest_w, on="week_start", how="left")
    panel["holiday_days"] = panel["holiday_days"].fillna(0)
    for col in ("temperature", "rainfall", "humidity"):
        panel[col] = panel[col].astype(float)
        panel[col] = panel.groupby("product_id")[col].transform(lambda s: s.fillna(s.median()))
        panel[col] = panel[col].fillna(panel[col].median())

    trends_file = PROCESSED_DIR / "google_trends.csv"
    if trends_file.exists():
        trends = pd.read_csv(trends_file)
        date_col = "week_start" if "week_start" in trends.columns else trends.columns[0]
        trends[date_col] = pd.to_datetime(trends[date_col])
        trends["week_start"] = _week_start(trends[date_col])
        long = trends.melt(
            id_vars=["week_start"],
            value_vars=[c for c in trends.columns if c not in {"week_start", date_col, "isPartial"}],
            var_name="trend_keyword",
            value_name="google_trend",
        )
        long["category"] = long["trend_keyword"].str.replace("_x", "", regex=False)
        panel = panel.merge(
            long[["week_start", "category", "google_trend"]],
            on=["week_start", "category"],
            how="left",
        )
    if "google_trend" not in panel.columns:
        panel["google_trend"] = np.nan

    panel = add_calendar(panel, "week_start")
    panel = panel.sort_values(["product_id", "week_start"])
    panel["festival_proximity"] = panel["holiday_days"].clip(0, 7)
    panel = panel.drop_duplicates(subset=["product_id", "week_start"], keep="last")
    dense = panel.copy()

    out = PROCESSED_DIR / "panel.parquet"
    dense.to_parquet(out, index=False)
    products.to_parquet(PROCESSED_DIR / "products.parquet", index=False)
    cold = mapping.loc[~mapping["has_history"], ["product_id", "category"]]
    cold.to_csv(PROCESSED_DIR / "cold_start_products.csv", index=False)

    summary = {
        "n_panel_rows": int(len(dense)),
        "n_products_with_history": int(mapping["has_history"].sum()),
        "n_cold_start_products": int((~mapping["has_history"]).sum()),
        "week_min": str(dense["week_start"].min()),
        "week_max": str(dense["week_start"].max()),
        "google_trend_coverage": float(dense["google_trend"].notna().mean()),
    }
    (PROCESSED_DIR / "preprocess_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return out


if __name__ == "__main__":
    path = preprocess()
    print(path)
