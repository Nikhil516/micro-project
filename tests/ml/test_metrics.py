from ml.evaluation.metrics import mae, rmse, wape


def test_metrics_known_values():
    y = [1, 2, 3]
    p = [1, 2, 4]
    assert abs(mae(y, p) - 1 / 3) < 1e-9
    assert rmse(y, p) > 0
    assert abs(wape(y, p) - (1 / 6)) < 1e-9
