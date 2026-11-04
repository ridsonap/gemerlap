#!/usr/bin/env python3
"""Uji validasi unduhan dataset spasial pemerintah (Kementan & BIG) dan evaluasi kesesuaian."""
import json
from pathlib import Path


def test_gov_datasets():
    dir_gov = Path("data/external_gov")
    p_plp2b = dir_gov / "kementan_plp2b_selayar_2025.geojson"
    p_big = dir_gov / "big_perkebunan_pertanian_selayar.geojson"

    assert p_plp2b.exists(), f"Berkas {p_plp2b} tidak ditemukan!"
    assert p_big.exists(), f"Berkas {p_big} tidak ditemukan!"

    # 1. Validasi Kementan PLP2B 2025
    with open(p_plp2b) as f:
        d_plp = json.load(f)
    assert len(d_plp["features"]) >= 1
    props_plp = d_plp["features"][0]["properties"]
    assert "Selayar" in props_plp["wadmkk"]
    assert props_plp["lbs"] > 1000, "LBS harus lebih dari 1.000 ha"

    # 2. Validasi BIG Perkebunan & Pertanian
    with open(p_big) as f:
        d_big = json.load(f)
    assert len(d_big["features"]) >= 50, "Jumlah fitur BIG tidak mencukupi"

    classes = set()
    for feat in d_big["features"]:
        c = feat["properties"].get("ptnobjname") or feat["properties"].get("namobj")
        classes.add(c)
    assert "Perkebunan" in classes
    assert "Tegalan/Ladang" in classes
    assert "Persawahan" in classes

    print("ALL GOV DATASET VALIDATION CHECKS PASSED!")


if __name__ == "__main__":
    test_gov_datasets()
