"""Fuse image PCA embeddings with lagged sales, product, calendar, and external features.

Scaling and one-hot encoding are fitted on the training period only (see train.py)
so test weeks do not leak into transformers.
"""

from __future__ import annotations

import json

import pandas as pd
from sklearn.decomposition import PCA

from ml.preprocessing.paths import MODELS_DIR, PROCESSED_DIR

PCA_DIM = 32
CAT_COLS = ["category", "colour", "pattern", "sleeve_type", "season"]
NUM_BASE = [
    "lag_1",
    "lag_2",
    "lag_4",
    "roll_mean_4",
    "roll_mean_8",
    "temperature_lag1",
    "rainfall_lag1",
    "humidity_lag1",
    "google_trend_lag1",
    "week_number",
    "month",
    "festival_proximity",
    "holiday_days",
]


def _add_lags(panel: pd.DataFrame) -> pd.DataFrame:
    panel = panel.sort_values(["product_id", "week_start"]).copy()
    panel["lag_1"] = panel.groupby("product_id")["units"].shift(1)
    panel["lag_2"] = panel.groupby("product_id")["units"].shift(2)
    panel["lag_4"] = panel.groupby("product_id")["units"].shift(4)
    shifted = panel.groupby("product_id")["units"].shift(1)
    panel["roll_mean_4"] = (
        shifted.groupby(panel["product_id"]).rolling(4, min_periods=1).mean().reset_index(level=0, drop=True)
    )
    panel["roll_mean_8"] = (
        shifted.groupby(panel["product_id"]).rolling(8, min_periods=1).mean().reset_index(level=0, drop=True)
    )
    panel["temperature_lag1"] = panel.groupby("product_id")["temperature"].shift(1)
    panel["rainfall_lag1"] = panel.groupby("product_id")["rainfall"].shift(1)
    panel["humidity_lag1"] = panel.groupby("product_id")["humidity"].shift(1)
    panel["google_trend_lag1"] = panel.groupby("product_id")["google_trend"].shift(1)
    panel["target"] = panel["units"]
    panel = panel[panel["lag_1"].notna()].copy()
    return panel


def fuse(pca_dim: int = PCA_DIM) -> pd.DataFrame:
    panel = pd.read_parquet(PROCESSED_DIR / "panel.parquet")
    products = pd.read_parquet(PROCESSED_DIR / "products.parquet")
    embeds = pd.read_parquet(PROCESSED_DIR / "image_embeddings.parquet")

    img_cols = [c for c in embeds.columns if c.startswith("img_")]
    n_comp = min(pca_dim, max(2, len(embeds) - 1), len(img_cols))
    pca = PCA(n_components=n_comp, random_state=42)
    reduced = pca.fit_transform(embeds[img_cols].values)
    pca_cols = [f"pca_{i}" for i in range(reduced.shape[1])]
    pca_df = pd.DataFrame(reduced, columns=pca_cols)
    pca_df["product_id"] = embeds["product_id"].values

    import joblib

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pca, MODELS_DIR / "image_pca.joblib")

    panel = panel.merge(products[["product_id", "colour", "pattern", "sleeve_type"]], on="product_id", how="left")
    panel = panel.merge(pca_df, on="product_id", how="inner")

    panel = _add_lags(panel)
    for col in [
        "lag_2",
        "lag_4",
        "temperature_lag1",
        "rainfall_lag1",
        "humidity_lag1",
        "google_trend_lag1",
        "festival_proximity",
        "holiday_days",
    ]:
        panel[col] = panel[col].fillna(0.0)

    keep = (
        ["product_id", "week_start", "target", "lag_1"]
        + NUM_BASE
        + CAT_COLS
        + pca_cols
    )
    # lag_1 appears twice in the list; drop duplicate column names when selecting
    ordered = []
    seen = set()
    for col in keep:
        if col not in seen and col in panel.columns:
            ordered.append(col)
            seen.add(col)
    fused = panel[ordered].copy()
    fused["lag_1_raw"] = fused["lag_1"]
    fused.to_parquet(PROCESSED_DIR / "fused_features.parquet", index=False)

    meta = {
        "numeric_features": NUM_BASE,
        "categorical_features": CAT_COLS,
        "pca_columns": pca_cols,
        "pca_dim": int(len(pca_cols)),
        "n_rows": int(len(fused)),
        "leakage_notes": (
            "Sales lags/rollings use only past weeks and stay inside each product. "
            "Weather and Google Trends are lagged 1 week. "
            "StandardScaler and OneHotEncoder are fitted on the chronological training split only. "
            "Calendar fields describe the target week (known in advance). "
            "PCA is fit on image embeddings (no sales labels)."
        ),
    }
    (MODELS_DIR / "feature_metadata.json").write_text(json.dumps(meta, indent=2))
    return fused


if __name__ == "__main__":
    print(fuse().shape)
