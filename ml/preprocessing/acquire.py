"""Download public datasets and external covariates."""

from __future__ import annotations

import io
import json
import ssl
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd
import certifi

from ml.preprocessing.paths import IMAGE_DIR, PROCESSED_DIR, RAW_DIR, ROOT, ensure_dirs

CLOTHING_ZIP = (
    "https://github.com/alexeygrigorev/clothing-dataset-small/archive/refs/heads/master.zip"
)
UCI_RETAIL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
UCI_RETAIL_CSV = (
    "https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/master/data/retail-data/all/online-retail-dataset.csv"
)
# College demo: keep catalog small so ResNet-50 can run on CPU.
MAX_IMAGES_PER_CATEGORY = 18
OPEN_METEO = (
    "https://archive-api.open-meteo.com/v1/archive"
    "?latitude=51.5072&longitude=-0.1276"
    "&start_date={start}&end_date={end}"
    "&daily=temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean"
    "&timezone=Europe%2FLondon"
)

FASHION_KEYWORDS = {
    "t-shirt": ["t-shirt", "tshirt", "tee"],
    "shirt": ["shirt", "blouse"],
    "dress": ["dress"],
    "pants": ["pant", "trouser", "jean", "legging"],
    "skirt": ["skirt"],
    "shorts": ["short"],
    "shoes": ["shoe", "boot", "sandal", "sneaker", "heel", "slipper"],
    "hat": ["hat", "cap", "beanie"],
    "outwear": ["jacket", "coat", "blazer", "parka", "hoodie", "cardigan"],
    "longsleeve": ["jumper", "sweater", "knit", "long sleeve", "pullover"],
}


def _download(url: str, dest: Path, timeout: int = 120) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    req = Request(url, headers={"User-Agent": "fashion-demand-forecasting/1.0"})
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(req, timeout=timeout, context=context) as resp:
        dest.write_bytes(resp.read())
    return dest


def download_clothing_images() -> Path:
    zip_path = RAW_DIR / "clothing-dataset-small.zip"
    _download(CLOTHING_ZIP, zip_path)
    extract_root = RAW_DIR / "clothing-dataset-small"
    if not extract_root.exists():
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(RAW_DIR)
        matches = list(RAW_DIR.glob("clothing-dataset-small-*"))
        if matches and not extract_root.exists():
            matches[0].rename(extract_root)
    return extract_root


def download_uci_retail() -> Path:
    zip_path = RAW_DIR / "online-retail.zip"
    xls_path = RAW_DIR / "Online Retail.xlsx"
    csv_path = RAW_DIR / "online-retail.csv"
    if xls_path.exists() and xls_path.stat().st_size > 0:
        return xls_path
    if csv_path.exists() and csv_path.stat().st_size > 0:
        return csv_path
    try:
        _download(UCI_RETAIL, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if name.lower().endswith((".xlsx", ".xls")):
                    xls_path.write_bytes(zf.read(name))
                    break
                if name.lower().endswith(".csv"):
                    csv_path.write_bytes(zf.read(name))
                    return csv_path
    except Exception:
        pass
    if xls_path.exists() and xls_path.stat().st_size > 0:
        return xls_path
    _download(UCI_RETAIL_CSV, csv_path, timeout=180)
    return csv_path


def _read_retail(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path, encoding="latin1")


def fetch_weather(start: date, end: date) -> pd.DataFrame:
    cache = RAW_DIR / f"weather_{start}_{end}.json"
    url = OPEN_METEO.format(start=start.isoformat(), end=end.isoformat())
    if not cache.exists():
        _download(url, cache, timeout=60)
    payload = json.loads(cache.read_text())
    daily = payload.get("daily") or {}
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(daily.get("time", [])),
            "temperature": daily.get("temperature_2m_mean", []),
            "rainfall": daily.get("precipitation_sum", []),
            "humidity": daily.get("relative_humidity_2m_mean", []),
        }
    )
    return frame


def fetch_google_trends(keywords: list[str], timeframe: str) -> pd.DataFrame | None:
    """Best-effort unofficial Trends pull. Returns None if blocked or missing."""
    cache = RAW_DIR / "google_trends.csv"
    if cache.exists():
        return pd.read_csv(cache, parse_dates=["week_start"])
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return None
    try:
        pytrends = TrendReq(hl="en-GB", tz=0)
        chunks = []
        for i in range(0, len(keywords), 5):
            batch = keywords[i : i + 5]
            pytrends.build_payload(batch, timeframe=timeframe, geo="GB")
            interest = pytrends.interest_over_time()
            if interest is None or interest.empty:
                continue
            interest = interest.reset_index().rename(columns={"date": "week_start"})
            chunks.append(interest)
        if not chunks:
            return None
        merged = chunks[0]
        for extra in chunks[1:]:
            merged = merged.merge(extra, on="week_start", how="outer")
        drop_cols = [c for c in merged.columns if c == "isPartial" or c.endswith("_y")]
        merged = merged.drop(columns=drop_cols, errors="ignore")
        merged.to_csv(cache, index=False)
        return merged
    except Exception:
        return None


def build_festival_table(start: date, end: date) -> pd.DataFrame:
    try:
        import holidays
    except ImportError as exc:
        raise RuntimeError("Install the holidays package") from exc
    cal = holidays.country_holidays("GB", years=range(start.year, end.year + 1))
    rows = []
    day = start
    while day <= end:
        rows.append(
            {
                "date": pd.Timestamp(day),
                "is_holiday": day in cal,
                "holiday_name": cal.get(day),
            }
        )
        day += timedelta(days=1)
    return pd.DataFrame(rows)


def infer_category(description: str) -> str | None:
    if description is None or pd.isna(description):
        return None
    text = str(description).lower()
    for category, keys in FASHION_KEYWORDS.items():
        if any(key in text for key in keys):
            return category
    return None


def copy_images(source_root: Path, max_per_category: int = MAX_IMAGES_PER_CATEGORY) -> pd.DataFrame:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    from collections import Counter

    counts: Counter[str] = Counter()
    rows = []
    for split in ("train", "validation", "test"):
        split_dir = source_root / split
        if not split_dir.exists():
            continue
        for category_dir in sorted(p for p in split_dir.iterdir() if p.is_dir()):
            category = category_dir.name
            for img in sorted(category_dir.glob("*.jpg")):
                if counts[category] >= max_per_category:
                    break
                dest = IMAGE_DIR / f"{category}_{split}_{img.name}"
                if not dest.exists():
                    dest.write_bytes(img.read_bytes())
                counts[category] += 1
                rows.append(
                    {
                        "product_id": dest.stem,
                        "category": category,
                        "image_path": str(dest.relative_to(ROOT)),
                        "split_source": split,
                    }
                )
    return pd.DataFrame(rows)


def attribute_defaults(category: str, product_id: str) -> dict:
    sleeve = {
        "t-shirt": "short",
        "shirt": "full",
        "longsleeve": "full",
        "dress": "sleeveless",
        "outwear": "full",
        "hat": "none",
        "shoes": "none",
        "pants": "none",
        "shorts": "none",
        "skirt": "none",
    }.get(category, "unknown")
    pattern = ["solid", "striped", "printed", "checked"][hash(product_id) % 4]
    colour = ["black", "white", "blue", "red", "beige", "green"][hash(product_id[::-1]) % 6]
    return {"sleeve_type": sleeve, "pattern": pattern, "colour": colour}


def acquire() -> dict[str, Path]:
    ensure_dirs()
    clothing_root = download_clothing_images()
    products = copy_images(clothing_root, max_per_category=MAX_IMAGES_PER_CATEGORY)
    if products.empty:
        raise RuntimeError("No clothing images found after download")
    attrs = products.apply(
        lambda row: pd.Series(attribute_defaults(row["category"], row["product_id"])),
        axis=1,
    )
    products = pd.concat([products, attrs], axis=1)
    products_path = PROCESSED_DIR / "products.csv"
    products.to_csv(products_path, index=False)

    retail_path = download_uci_retail()
    retail = _read_retail(retail_path)
    retail.columns = [c.strip() for c in retail.columns]
    retail = retail.dropna(subset=["Description", "InvoiceDate"])
    retail["Quantity"] = pd.to_numeric(retail["Quantity"], errors="coerce").fillna(0)
    retail = retail[retail["Quantity"] != 0]
    retail["category"] = retail["Description"].map(infer_category)
    fashion = retail[retail["category"].notna()].copy()
    fashion["week_start"] = (
        pd.to_datetime(fashion["InvoiceDate"]).dt.tz_localize(None).dt.to_period("W-SUN").dt.start_time
    )
    weekly = (
        fashion.groupby(["StockCode", "category", "week_start"], as_index=False)["Quantity"]
        .sum()
        .rename(columns={"StockCode": "stock_code", "Quantity": "units"})
    )
    weekly["stock_code"] = weekly["stock_code"].astype(str)
    weekly["units"] = weekly["units"].clip(lower=0)
    weekly_path = PROCESSED_DIR / "uci_weekly_fashion.csv"
    weekly.to_csv(weekly_path, index=False)

    start = weekly["week_start"].min().date() - timedelta(days=7)
    end = weekly["week_start"].max().date() + timedelta(days=7)
    weather = fetch_weather(start, end)
    weather.to_csv(PROCESSED_DIR / "weather_daily.csv", index=False)
    festivals = build_festival_table(start, end)
    festivals.to_csv(PROCESSED_DIR / "festivals.csv", index=False)

    keywords = list(FASHION_KEYWORDS.keys())
    timeframe = f"{start.isoformat()} {end.isoformat()}"
    trends = fetch_google_trends(keywords, timeframe)
    trends_path = PROCESSED_DIR / "google_trends.csv"
    if trends is not None:
        trends.to_csv(trends_path, index=False)

    meta = {
        "acquired_at": datetime.utcnow().isoformat() + "Z",
        "n_products": int(len(products)),
        "n_weekly_rows": int(len(weekly)),
        "google_trends": bool(trends is not None),
        "sources": {
            "images": CLOTHING_ZIP,
            "sales": str(retail_path),
            "weather": "Open-Meteo London archive",
        },
    }
    meta_path = PROCESSED_DIR / "acquisition_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    return {
        "products": products_path,
        "weekly": weekly_path,
        "weather": PROCESSED_DIR / "weather_daily.csv",
        "festivals": PROCESSED_DIR / "festivals.csv",
        "meta": meta_path,
    }


if __name__ == "__main__":
    print(json.dumps({k: str(v) for k, v in acquire().items()}, indent=2))
