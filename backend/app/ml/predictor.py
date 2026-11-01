"""Load trained artifacts and generate weekly demand predictions."""

from __future__ import annotations

import json
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.config import ROOT, settings

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


class ForecastService:
    def __init__(self) -> None:
        configured_dir = Path(settings.model_dir)
        self.model_dir = configured_dir if configured_dir.is_absolute() else ROOT / configured_dir
        self.artifact = None
        self.encoder = None
        self.scaler = None
        self.pca = None
        self.embeddings = None
        self.embed_ids = []
        self.feature_names: list[str] = []
        self.metrics: dict = {}
        self.importance: dict = {}
        self.resnet_meta: dict = {}
        self.available = False
        self.status = "artifacts_missing"
        self._load()

    def _load(self) -> None:
        model_path = self.model_dir / "xgboost_weekly_demand.joblib"
        if not model_path.exists():
            self.status = f"missing {model_path}"
            return
        try:
            self.artifact = joblib.load(model_path)
            self.encoder = joblib.load(self.model_dir / "onehot_encoder.joblib")
            self.scaler = joblib.load(self.model_dir / "numeric_scaler.joblib")
            self.pca = joblib.load(self.model_dir / "image_pca.joblib")
            self.feature_names = self.artifact["feature_names"]
            metrics_path = self.model_dir / "evaluation_metrics.json"
            imp_path = self.model_dir / "feature_importance.json"
            self.metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else self.artifact.get("metrics", {})
            self.importance = json.loads(imp_path.read_text()) if imp_path.exists() else {}
            cfg = self.model_dir / "resnet50_config.json"
            self.resnet_meta = json.loads(cfg.read_text()) if cfg.exists() else {}
            npy = self.model_dir / "resnet50_embeddings.npy"
            ids = self.model_dir / "resnet50_product_ids.json"
            if npy.exists() and ids.exists():
                self.embeddings = np.load(npy)
                self.embed_ids = json.loads(ids.read_text())
            self.available = True
            self.status = "ready"
        except Exception as exc:  # noqa: BLE001 — report load failures to /model
            self.status = f"load_error: {exc}"
            self.available = False

    def model_info(self) -> dict:
        return {
            "available": self.available,
            "status": self.status,
            "model_version": (self.metrics or {}).get("model_version") or (self.artifact or {}).get("model_version"),
            "trained_at": (self.metrics or {}).get("trained_at"),
            "metrics": (self.metrics or {}).get("model"),
            "baseline_metrics": (self.metrics or {}).get("naive_lag1_baseline"),
            "hyperparameters": (self.metrics or {}).get("hyperparameters"),
            "split": (self.metrics or {}).get("split"),
            "feature_importance": dict(list(self.importance.items())[:40]),
            "resnet50": self.resnet_meta,
            "disclaimer": (
                "Feature importance ranks split gain inside XGBoost. It is not a causal statement. "
                "Metrics are computed on a chronological hold-out from the aligned UCI + clothing-image panel."
            ),
        }

    def _pca_vector(self, product_id: str, raw_embedding: np.ndarray | None = None) -> np.ndarray:
        dim = int(self.pca.n_components_)
        if raw_embedding is not None:
            return self.pca.transform(raw_embedding.reshape(1, -1))[0]
        if self.embeddings is None:
            return np.zeros(dim)
        try:
            idx = self.embed_ids.index(product_id)
            return self.pca.transform(self.embeddings[idx].reshape(1, -1))[0]
        except ValueError:
            return np.zeros(dim)

    def register_image_embedding(self, product_id: str, image_data: bytes) -> None:
        if not self.available or self.pca is None:
            raise RuntimeError("trained model artifacts are unavailable")
        if not image_data:
            raise ValueError("image is empty")

        from ml.feature_extraction.resnet import embed_single

        with tempfile.NamedTemporaryFile(suffix=".jpg") as temp:
            temp.write(image_data)
            temp.flush()
            embedding = embed_single(temp.name).astype(np.float32)

        if embedding.shape != (2048,):
            raise ValueError(f"unexpected ResNet-50 embedding shape: {embedding.shape}")
        if self.embeddings is None:
            embeddings = embedding.reshape(1, -1)
            ids = [product_id]
        else:
            keep = [index for index, value in enumerate(self.embed_ids) if value != product_id]
            embeddings = np.vstack([self.embeddings[keep], embedding])
            ids = [self.embed_ids[index] for index in keep] + [product_id]

        np.save(self.model_dir / "resnet50_embeddings.npy", embeddings)
        (self.model_dir / "resnet50_product_ids.json").write_text(json.dumps(ids))
        self.embeddings = embeddings
        self.embed_ids = ids

    def _similar_ids(self, product_id: str, k: int = 8) -> list[str]:
        if self.embeddings is None or product_id not in self.embed_ids:
            return []
        idx = self.embed_ids.index(product_id)
        vec = self.embeddings[idx]
        sims = self.embeddings @ vec / (
            np.linalg.norm(self.embeddings, axis=1) * (np.linalg.norm(vec) + 1e-9) + 1e-9
        )
        order = np.argsort(-sims)
        out = []
        for j in order:
            pid = self.embed_ids[int(j)]
            if pid != product_id:
                out.append(pid)
            if len(out) >= k:
                break
        return out

    def _calendar(self, week_start: date) -> dict:
        dt = pd.Timestamp(week_start)
        return {
            "week_number": int(dt.isocalendar().week),
            "month": int(dt.month),
            "season": SEASON_MAP[int(dt.month)],
            "festival_proximity": 0.0,
            "holiday_days": 0.0,
        }

    def predict_product(
        self,
        product: dict,
        history: list[dict],
        horizon_weeks: int = 4,
        weather: dict | None = None,
        google_trend: float = 0.0,
        holiday_days: float = 0.0,
    ) -> dict:
        if not self.available:
            raise RuntimeError(self.status)

        hist = pd.DataFrame(history)
        if not hist.empty:
            hist["date"] = pd.to_datetime(hist["date"])
            hist["week_start"] = hist["date"].dt.to_period("W-SUN").dt.start_time
            weekly = hist.groupby("week_start", as_index=False)["quantity"].sum().rename(columns={"quantity": "units"})
            weekly = weekly.sort_values("week_start")
        else:
            weekly = pd.DataFrame(columns=["week_start", "units"])

        cold_start = len(weekly) < 4
        last_week = (
            weekly["week_start"].max().date()
            if not weekly.empty
            else date.today() - timedelta(days=date.today().weekday())
        )
        units_list = weekly["units"].tolist() if not weekly.empty else []

        pca_vec = self._pca_vector(product["product_id"])
        weather = weather or {}
        forecasts = []
        cursor_units = list(units_list)

        for step in range(horizon_weeks):
            target_week = last_week + timedelta(days=7 * (step + 1))
            cal = self._calendar(target_week)
            cal["holiday_days"] = holiday_days if step == 0 else 0.0
            cal["festival_proximity"] = cal["holiday_days"]

            lag_1 = cursor_units[-1] if cursor_units else 0.0
            lag_2 = cursor_units[-2] if len(cursor_units) > 1 else 0.0
            lag_4 = cursor_units[-4] if len(cursor_units) > 3 else 0.0
            roll_4 = float(np.mean(cursor_units[-4:])) if cursor_units else 0.0
            roll_8 = float(np.mean(cursor_units[-8:])) if cursor_units else 0.0

            numeric = {
                "lag_1": lag_1,
                "lag_2": lag_2,
                "lag_4": lag_4,
                "roll_mean_4": roll_4,
                "roll_mean_8": roll_8,
                "temperature_lag1": float(weather.get("temperature") or 0),
                "rainfall_lag1": float(weather.get("rainfall") or 0),
                "humidity_lag1": float(weather.get("humidity") or 0),
                "google_trend_lag1": float(google_trend or 0),
                "week_number": cal["week_number"],
                "month": cal["month"],
                "festival_proximity": cal["festival_proximity"],
                "holiday_days": cal["holiday_days"],
            }
            meta = json.loads((self.model_dir / "feature_metadata.json").read_text())
            num_order = meta["numeric_features"]
            x_num = self.scaler.transform(np.array([[numeric[k] for k in num_order]], dtype=float))
            cats = pd.DataFrame(
                [
                    {
                        "category": product.get("category", "unknown"),
                        "colour": product.get("colour", "unknown"),
                        "pattern": product.get("pattern", "solid"),
                        "sleeve_type": product.get("sleeve_type", "unknown"),
                        "season": cal["season"],
                    }
                ]
            )
            x_cat = self.encoder.transform(cats.astype(str))
            x = np.hstack([x_num, x_cat, pca_vec.reshape(1, -1)])
            col_names = meta["feature_names"]
            frame = pd.DataFrame(x, columns=col_names)[self.feature_names]
            yhat = float(np.clip(self.artifact["model"].predict(frame.values)[0], 0, None))

            method = "xgboost_history"
            if cold_start:
                method = "xgboost_cold_start"
            forecasts.append(
                {
                    "week_start": target_week.isoformat(),
                    "predicted_units": round(yhat, 2),
                    "method": method,
                    "cold_start": cold_start,
                }
            )
            cursor_units.append(yhat)

        similar = self._similar_ids(product["product_id"]) if cold_start else []
        return {
            "product_id": product["product_id"],
            "horizon_weeks": horizon_weeks,
            "cold_start": cold_start,
            "cold_start_note": (
                "Fewer than 4 historical weeks. Prediction relies on image PCA, attributes, "
                "and calendar/external covariates. Reliability is lower than history-based forecasts."
                if cold_start
                else None
            ),
            "similar_product_ids": similar,
            "forecasts": forecasts,
            "model_version": self.artifact.get("model_version"),
            "explainability": {
                "top_features": dict(list(self.importance.items())[:12]),
                "caveat": "Global feature importance, not a per-row causal explanation.",
            },
        }


forecast_service = ForecastService()
