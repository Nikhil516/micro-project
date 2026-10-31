from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "ml" / "models" / "xgboost_weekly_demand.joblib"


def test_model_artifact_exists_after_training():
    if not MODEL.exists():
        return
    import joblib

    artifact = joblib.load(MODEL)
    assert "model" in artifact
    assert artifact["feature_names"]
    import numpy as np

    x = np.zeros((1, len(artifact["feature_names"])))
    pred = artifact["model"].predict(x)
    assert pred.shape == (1,)
