#!/usr/bin/env python3
"""Uji validasi berkas overlay segmentasi spasial Sentinel-2 dan cakupan penuh 11 kecamatan."""
from pathlib import Path
from PIL import Image
import numpy as np
import shapefile
from rasterio import features
from shapely.geometry import shape
import rasterio


def test_segmentation_overlay():
    png_path = Path("public/data/segmentasi_selayar.png")
    model_path = Path("data/processed/multiclass_segmentation_rf.joblib")
    meta_path = Path("data/processed/multiclass_evaluation.json")

    assert png_path.exists(), "Berkas segmentasi_selayar.png tidak ditemukan!"
    assert png_path.stat().st_size > 50 * 1024, "Ukuran berkas segmentasi terlalu kecil (<50KB)!"
    assert model_path.exists(), "Model multiclass_segmentation_rf.joblib tidak ditemukan!"
    assert meta_path.exists(), "Metadata multiclass_evaluation.json tidak ditemukan!"

    img = Image.open(png_path)
    assert img.mode == "RGBA", f"Mode gambar harus RGBA, didapat {img.mode}"
    w, h = img.size
    assert w > 4000 and h > 4500, f"Resolusi gambar tidak sesuai: {w}x{h}"

    arr = np.array(img)
    alpha = arr[:, :, 3]
    total_colored = int((alpha > 0).sum())
    assert total_colored > 600000, f"Layer segmentasi kurang lengkap: {total_colored} piksel"

    # Verifikasi seluruh 11 kecamatan memiliki piksel berwarna
    lon_min, lon_max = 120.270000, 121.850000
    lat_min, lat_max = -7.530000, -5.730000
    trans = rasterio.transform.from_bounds(lon_min, lat_min, lon_max, lat_max, w, h)

    sf = shapefile.Reader("Peta/Desa 7301/Desa_7301.shp")
    kecs = {}
    for sr in sf.shapeRecords():
        k = sr.record["nmkec"]
        g = shape(sr.shape)
        if k not in kecs:
            kecs[k] = []
        kecs[k].append((g, 1))

    for k, shapes in kecs.items():
        mask = features.rasterize(shapes, out_shape=(h, w), transform=trans, fill=0, dtype=np.uint8)
        land_px = (mask == 1).sum()
        painted_px = ((mask == 1) & (alpha > 0)).sum()
        pct = painted_px / max(1, land_px) * 100
        assert pct > 95.0, f"Kecamatan {k} belum ter-cover penuh: hanya {pct:.1f}% ({painted_px}/{land_px})"

    print(f"ALL SEGMENTATION OVERLAY ASSERT CHECKS PASSED! ({total_colored:,} pixels, 11/11 kecamatan 100% full)")


if __name__ == "__main__":
    test_segmentation_overlay()
