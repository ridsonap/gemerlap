#!/usr/bin/env python3
"""Assert check for trained models, predictions, and benchmark outputs."""
import json
from pathlib import Path
import rasterio

PROCESSED_DIR = Path("data/processed")


def test_train_and_predict():
    # 1. Benchmark JSON check
    bm_path = PROCESSED_DIR / "model_benchmark.json"
    assert bm_path.exists(), f"Missing {bm_path}"
    with open(bm_path) as f:
        bm = json.load(f)
    assert "benchmark" in bm and "best_model" in bm
    assert len(bm["benchmark"]) == 4, f"Expected 4 models, got {len(bm['benchmark'])}"
    for m_name in ["LightGBM", "RandomForest", "LogisticRegression", "GaussianNB"]:
        assert m_name in bm["benchmark"], f"Missing {m_name}"
        score = bm["benchmark"][m_name]["f1_score"]
        assert 0.85 <= score <= 1.0, f"{m_name} F1 out of expected range: {score}"

    # 2. Desa prediction summary check
    desa_path = PROCESSED_DIR / "desa_coconut_predictions.json"
    assert desa_path.exists(), f"Missing {desa_path}"
    with open(desa_path) as f:
        desa_data = json.load(f)
    assert len(desa_data) == 34, f"Expected 34 desa, got {len(desa_data)}"
    sample = next(iter(desa_data.values()))
    assert "predicted_coconut_ha" in sample and "mean_confidence" in sample
    assert sample["predicted_coconut_ha"] >= 0.0

    # 3. Prediction GeoTIFF check
    tif_path = PROCESSED_DIR / "S2A_51MTN_coconut_prediction.tif"
    assert tif_path.exists(), f"Missing {tif_path}"
    with rasterio.open(tif_path) as src:
        assert src.count == 2, f"Expected 2 bands, got {src.count}"
        assert src.nodata == 255
        assert src.dtypes == ("uint8", "uint8")

    print("ALL MODEL & PREDICTION ASSERT CHECKS PASSED!")


if __name__ == "__main__":
    test_train_and_predict()
