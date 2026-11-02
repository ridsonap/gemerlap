#!/usr/bin/env python3
"""Self-check for processed Sentinel-2 outputs."""
import json
from pathlib import Path
import numpy as np
import rasterio

PROCESSED_DIR = Path("data/processed")
SCENE_ID = "S2A_51MTN_20241027_0_L2A"


def test_processed_outputs():
    # 1. Check NPZ features
    npz_path = PROCESSED_DIR / f"{SCENE_ID}_features.npz"
    assert npz_path.exists(), f"Missing {npz_path}"
    data = np.load(npz_path)
    assert "features" in data and "feature_names" in data
    assert data["features"].shape[1] == 18, f"Expected 18 features, got {data['features'].shape[1]}"
    n_pix = data["features"].shape[0]
    assert n_pix > 2_000_000, f"Expected >2M pixels, got {n_pix}"

    # Lon/lat within Kepulauan Selayar bounds
    lon_min, lon_max = data["lon"].min(), data["lon"].max()
    lat_min, lat_max = data["lat"].min(), data["lat"].max()
    assert 120.0 <= lon_min and lon_max <= 122.0, f"Lon out of bounds: [{lon_min}, {lon_max}]"
    assert -8.0 <= lat_min and lat_max <= -5.5, f"Lat out of bounds: [{lat_min}, {lat_max}]"

    # NDVI feature in column index 10
    ndvi_idx = list(data["feature_names"]).index("NDVI")
    ndvi = data["features"][:, ndvi_idx]
    assert -1.0 <= ndvi.min() and ndvi.max() <= 1.0, f"NDVI out of range: [{ndvi.min()}, {ndvi.max()}]"

    # 2. Check JSON summary
    json_path = PROCESSED_DIR / f"{SCENE_ID}_desa_summary.json"
    assert json_path.exists(), f"Missing {json_path}"
    with open(json_path) as f:
        summary = json.load(f)
    assert len(summary) == 34, f"Expected 34 desa, got {len(summary)}"
    sample_desa = next(iter(summary.values()))
    for key in ["total_land_ha", "vegetation_ha", "coconut_candidate_ha", "mean_ndvi", "mean_ndre1"]:
        assert key in sample_desa, f"Missing key {key} in summary"

    # 3. Check GeoTIFF indices
    tif_path = PROCESSED_DIR / f"{SCENE_ID}_indices.tif"
    assert tif_path.exists(), f"Missing {tif_path}"
    with rasterio.open(tif_path) as src:
        assert src.count == 4, f"Expected 4 bands, got {src.count}"
        assert str(src.crs) == "EPSG:32751", f"Expected EPSG:32751, got {src.crs}"
        assert src.nodata == -9999.0

    print("ALL ASSERT CHECKS PASSED!")


if __name__ == "__main__":
    test_processed_outputs()
