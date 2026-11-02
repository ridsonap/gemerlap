#!/usr/bin/env python3
"""Assert check for dashboard data integration and stats consistency."""
import json
from pathlib import Path

PUB_DATA = Path("public/data")


def test_dashboard_stats():
    # 1. Stats JSON validation
    stats_file = PUB_DATA / "stats.json"
    assert stats_file.exists(), f"Missing {stats_file}"
    with open(stats_file) as f:
        stats = json.load(f)

    meta = stats["meta"]
    assert "Sentinel-2" in meta["sumber"]
    assert meta["satuan"] == "hektar (ha)"

    kab = stats["kabupaten"]
    total_kab = kab["total_ha"]
    assert 110_000.0 <= total_kab <= 125_000.0, f"Unexpected kabupaten area: {total_kab}"
    kelapa_kab = kab["kelas"]["kelapa"]
    assert 25_000.0 <= kelapa_kab <= 40_000.0, f"Unexpected coconut area: {kelapa_kab}"

    # Sum of classes matches total
    class_sum = sum(kab["kelas"].values())
    assert abs(class_sum - total_kab) < 2.0, f"Class sum {class_sum} != total {total_kab}"

    # 2. Kecamatan validation (11 kecamatan)
    kecs = stats["kecamatan"]
    assert len(kecs) == 11, f"Expected 11 kecamatan, got {len(kecs)}"
    sum_kec_total = sum(v["total_ha"] for v in kecs.values())
    assert abs(sum_kec_total - total_kab) < 2.0, f"Kec sum {sum_kec_total} != kab total {total_kab}"

    # 3. Desa GeoJSON validation (88 desa)
    desa_file = PUB_DATA / "desa.geojson"
    assert desa_file.exists(), f"Missing {desa_file}"
    with open(desa_file) as f:
        fc = json.load(f)
    assert len(fc["features"]) == 88, f"Expected 88 desa, got {len(fc['features'])}"

    for feat in fc["features"]:
        p = feat["properties"]
        assert "total_ha" in p and p["total_ha"] > 0
        assert "dominan" in p and p["dominan"] in kab["kelas"]

    print("ALL DASHBOARD STATS ASSERT CHECKS PASSED!")


if __name__ == "__main__":
    test_dashboard_stats()
