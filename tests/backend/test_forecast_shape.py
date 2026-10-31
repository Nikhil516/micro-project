from datetime import date


def test_predict_product_requires_loaded_model():
    from app.ml.predictor import ForecastService

    svc = ForecastService.__new__(ForecastService)
    svc.available = False
    svc.status = "artifacts_missing"
    try:
        svc.predict_product({"product_id": "x", "category": "dress"}, [])
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "artifacts_missing" in str(exc)


def test_calendar_week_fields():
    from app.ml.predictor import ForecastService

    svc = ForecastService.__new__(ForecastService)
    cal = ForecastService._calendar(svc, date(2011, 6, 6))
    assert cal["month"] == 6
    assert cal["season"] == "summer"
    assert cal["week_number"] >= 1
