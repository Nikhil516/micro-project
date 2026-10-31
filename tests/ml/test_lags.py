import pandas as pd

from ml.feature_extraction.fusion import _add_lags


def test_lags_use_only_past():
    frame = pd.DataFrame(
        {
            "product_id": ["a"] * 5,
            "week_start": pd.date_range("2020-01-06", periods=5, freq="7D"),
            "units": [10, 20, 30, 40, 50],
            "temperature": [1, 2, 3, 4, 5],
            "rainfall": 0,
            "humidity": 0,
            "google_trend": 0,
        }
    )
    out = _add_lags(frame)
    row = out.iloc[-1]
    assert row["lag_1"] == 40
    assert row["target"] == 50
    assert row["lag_1"] != row["target"]


def test_rolling_does_not_cross_products():
    frame = pd.DataFrame(
        {
            "product_id": ["a", "a", "b", "b"],
            "week_start": pd.to_datetime(["2020-01-06", "2020-01-13", "2020-01-06", "2020-01-13"]),
            "units": [100, 200, 1, 2],
            "temperature": 0,
            "rainfall": 0,
            "humidity": 0,
            "google_trend": 0,
        }
    )
    out = _add_lags(frame)
    b = out[out["product_id"] == "b"].iloc[0]
    assert b["lag_1"] == 1
    assert b["roll_mean_4"] == 1
