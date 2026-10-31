"""Chronological XGBoost training, baseline comparison, artifact export."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

from ml.evaluation.metrics import mae, rmse, wape
from ml.feature_extraction.fusion import CAT_COLS, NUM_BASE
from ml.preprocessing.paths import MODELS_DIR, PROCESSED_DIR, ensure_dirs

MODEL_PATH = MODELS_DIR / "xgboost_weekly_demand.joblib"


def chrono_split(frame: pd.DataFrame, val_weeks: int = 6, test_weeks: int = 6):
    weeks = np.sort(frame["week_start"].unique())
    if len(weeks) < val_weeks + test_weeks + 8:
        val_weeks = max(2, len(weeks) // 6)
        test_weeks = max(2, len(weeks) // 6)
    test_cut = weeks[-test_weeks]
    val_cut = weeks[-(test_weeks + val_weeks)]
    train = frame[frame["week_start"] < val_cut]
    val = frame[(frame["week_start"] >= val_cut) & (frame["week_start"] < test_cut)]
    test = frame[frame["week_start"] >= test_cut]
    if train.empty or test.empty:
        raise RuntimeError("Chronological split produced an empty train or test set")
    return train, val, test, {"val_cut": str(val_cut), "test_cut": str(test_cut)}


def naive_baseline(frame: pd.DataFrame) -> np.ndarray:
    return frame["lag_1_raw"].fillna(0).astype(float).values


def _encode_split(frame: pd.DataFrame, encoder: OneHotEncoder, scaler: StandardScaler, pca_cols: list[str], feature_names: list[str] | None = None):
    x_num = scaler.transform(frame[NUM_BASE].astype(float))
    x_cat = encoder.transform(frame[CAT_COLS].astype(str))
    x_pca = frame[pca_cols].astype(float).values
    x = np.hstack([x_num, x_cat, x_pca])
    names = NUM_BASE + list(encoder.get_feature_names_out(CAT_COLS)) + pca_cols
    if feature_names is not None:
        table = pd.DataFrame(x, columns=names)
        x = table[feature_names].values
        names = feature_names
    y = frame["target"].astype(float).values
    return x, y, names


def train_xgb(image_limit: int | None = None) -> dict:
    ensure_dirs()
    from ml.feature_extraction.fusion import fuse
    from ml.feature_extraction.resnet import extract_embeddings
    from ml.preprocessing.acquire import acquire
    from ml.preprocessing.clean import preprocess

    if not (PROCESSED_DIR / "products.csv").exists():
        acquire()
    if not (PROCESSED_DIR / "panel.parquet").exists():
        preprocess()
    if not (PROCESSED_DIR / "image_embeddings.parquet").exists():
        extract_embeddings(image_limit=image_limit)

    fused = fuse()
    meta = json.loads((MODELS_DIR / "feature_metadata.json").read_text())
    pca_cols = meta["pca_columns"]

    train, val, test, cuts = chrono_split(fused)

    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    encoder.fit(train[CAT_COLS].astype(str))
    scaler = StandardScaler()
    scaler.fit(train[NUM_BASE].astype(float))

    x_train, y_train, feature_names = _encode_split(train, encoder, scaler, pca_cols)
    x_val, y_val, _ = _encode_split(val, encoder, scaler, pca_cols, feature_names) if len(val) else (None, None, feature_names)
    x_test, y_test, _ = _encode_split(test, encoder, scaler, pca_cols, feature_names)

    joblib.dump(encoder, MODELS_DIR / "onehot_encoder.joblib")
    joblib.dump(scaler, MODELS_DIR / "numeric_scaler.joblib")
    meta["feature_names"] = feature_names
    meta["n_train"] = int(len(train))
    meta["n_val"] = int(len(val))
    meta["n_test"] = int(len(test))
    (MODELS_DIR / "feature_metadata.json").write_text(json.dumps(meta, indent=2))

    param_grid = [
        {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05, "subsample": 0.8, "colsample_bytree": 0.8},
        {"n_estimators": 300, "max_depth": 6, "learning_rate": 0.03, "subsample": 0.9, "colsample_bytree": 0.7},
        {"n_estimators": 150, "max_depth": 3, "learning_rate": 0.1, "subsample": 0.8, "colsample_bytree": 0.9},
    ]
    best = None
    best_val = float("inf")
    for params in param_grid:
        model = XGBRegressor(
            objective="reg:squarederror",
            random_state=42,
            n_jobs=2,
            tree_method="hist",
            **params,
        )
        model.fit(x_train, y_train, verbose=False)
        preds = model.predict(x_val) if x_val is not None and len(val) else model.predict(x_train)
        truth = y_val if x_val is not None and len(val) else y_train
        score = mae(truth, preds)
        if score < best_val:
            best_val = score
            best = (model, params)

    model, params = best
    y_hat = np.clip(model.predict(x_test), 0, None)
    naive = naive_baseline(test)

    metrics = {
        "model": {
            "mae": mae(y_test, y_hat),
            "rmse": rmse(y_test, y_hat),
            "wape": wape(y_test, y_hat),
        },
        "naive_lag1_baseline": {
            "mae": mae(y_test, naive),
            "rmse": rmse(y_test, naive),
            "wape": wape(y_test, naive),
        },
        "hyperparameters": params,
        "split": cuts,
        "n_train": int(len(train)),
        "n_val": int(len(val)),
        "n_test": int(len(test)),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_version": "xgb-weekly-v1",
    }

    importance = dict(zip(feature_names, model.feature_importances_.astype(float).tolist()))
    importance = dict(sorted(importance.items(), key=lambda kv: kv[1], reverse=True))
    metrics["feature_importance_top30"] = dict(list(importance.items())[:30])

    artifact = {
        "model": model,
        "feature_names": feature_names,
        "metrics": metrics,
        "model_version": metrics["model_version"],
        "trained_at": metrics["trained_at"],
    }
    joblib.dump(artifact, MODEL_PATH)
    (MODELS_DIR / "evaluation_metrics.json").write_text(json.dumps(metrics, indent=2))
    (MODELS_DIR / "feature_importance.json").write_text(json.dumps(importance, indent=2))

    pred_frame = test[["product_id", "week_start", "target"]].copy()
    pred_frame["prediction"] = y_hat
    pred_frame["baseline"] = naive
    pred_frame.to_csv(MODELS_DIR / "test_predictions.csv", index=False)
    return metrics


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing trained model at {MODEL_PATH}")
    return joblib.load(MODEL_PATH)


def smoke_predict() -> dict:
    artifact = load_model()
    encoder = joblib.load(MODELS_DIR / "onehot_encoder.joblib")
    scaler = joblib.load(MODELS_DIR / "numeric_scaler.joblib")
    fused = pd.read_parquet(PROCESSED_DIR / "fused_features.parquet")
    meta = json.loads((MODELS_DIR / "feature_metadata.json").read_text())
    row = fused.tail(1)
    x, _, _ = _encode_split(row, encoder, scaler, meta["pca_columns"], artifact["feature_names"])
    pred = float(np.clip(artifact["model"].predict(x)[0], 0, None))
    return {"product_id": row["product_id"].iloc[0], "prediction": pred}


if __name__ == "__main__":
    result = train_xgb()
    print(json.dumps(result, indent=2))
    print("smoke", smoke_predict())
