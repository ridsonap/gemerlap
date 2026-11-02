#!/usr/bin/env python3
"""Uji validasi berkas overlay segmentasi spasial Sentinel-2."""
from pathlib import Path
from PIL import Image
import numpy as np


def test_segmentation_overlay():
    png_path = Path("public/data/segmentasi_selayar.png")
    assert png_path.exists(), "Berkas segmentasi_selayar.png tidak ditemukan!"
    assert png_path.stat().st_size > 50 * 1024, "Ukuran berkas segmentasi terlalu kecil (<50KB)!"

    img = Image.open(png_path)
    assert img.mode == "RGBA", f"Mode gambar harus RGBA, didapat {img.mode}"
    w, h = img.size
    assert w > 2000 and h > 4000, f"Resolusi gambar tidak sesuai: {w}x{h}"

    arr = np.array(img)
    alpha = arr[:, :, 3]
    assert (alpha > 0).sum() > 100000, "Layer segmentasi tidak memiliki piksel berwarna!"

    print("ALL SEGMENTATION OVERLAY ASSERT CHECKS PASSED!")


if __name__ == "__main__":
    test_segmentation_overlay()
