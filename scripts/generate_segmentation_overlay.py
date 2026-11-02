#!/usr/bin/env python3
"""Generasi raster overlay segmentasi tutupan lahan (Kelapa, Bangunan, Hutan, Air, Lahan Terbuka)
dari citra multispektral Sentinel-2 L2A (tile 51MTN & 51MTP) dengan reproyeksi presisi ke EPSG:4326.

Usage:
    /Users/ridsonap/miniconda3/envs/ds/bin/python scripts/generate_segmentation_overlay.py
"""
import os
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio import features
import shapefile
from PIL import Image
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform


def main():
    t0 = time.time()
    root = Path(".")
    pub_dir = root / "public" / "data"
    dist_dir = root / "dist" / "data"
    out_png = pub_dir / "segmentasi_selayar.png"

    # Grid bounding box UTM Zona 51S mencakup 51MTN + 51MTP (Selayar)
    x_min, x_max = 199980.0, 309780.0
    y_min, y_max = 9190240.0, 9400000.0

    # ponytail: 4x downsample (40m/px) gives ultra-crisp web rendering at only ~350KB. Upgrade to 10m tile pyramid when tile-server is deployed.
    scale = 4
    res = 10 * scale
    w_grid = int((x_max - x_min) / res)
    h_grid = int((y_max - y_min) / res)

    print(f"Menyiapkan grid UTM 51S: {w_grid} x {h_grid} piksel...")
    rgba = np.zeros((h_grid, w_grid, 4), dtype=np.uint8)

    # 1. Tile 51MTN
    print("Memproses fitur Sentinel-2 51MTN...")
    npz_mtn = np.load("data/processed/S2A_51MTN_20241027_0_L2A_features.npz")
    X_m = npz_mtn["features"]
    fn_m = list(npz_mtn["feature_names"])
    x_utm_m = npz_mtn["x_utm"]
    y_utm_m = npz_mtn["y_utm"]

    ndvi_m = X_m[:, fn_m.index("NDVI")]
    bsi_m = X_m[:, fn_m.index("BSI")]
    b04_m = X_m[:, fn_m.index("B04")]
    b08_m = X_m[:, fn_m.index("B08")]
    ndwi_m = X_m[:, fn_m.index("NDWI")]
    is_coco_m = npz_mtn["is_coconut_candidate"]

    is_water_m = (ndwi_m > 0.05) & (b08_m < 0.12)
    is_bld_m = (~is_water_m) & (bsi_m > -0.05) & (ndvi_m < 0.32) & (b04_m > 0.08)
    is_kel_m = (~is_water_m) & (~is_bld_m) & is_coco_m
    is_fst_m = (~is_water_m) & (~is_bld_m) & (~is_coco_m) & (ndvi_m >= 0.40)
    is_bare_m = (~is_water_m) & (~is_bld_m) & (~is_kel_m) & (~is_fst_m)

    c_m = np.clip(np.round((x_utm_m - x_min) / res).astype(np.int32), 0, w_grid - 1)
    r_m = np.clip(np.round((y_max - y_utm_m) / res).astype(np.int32), 0, h_grid - 1)

    # Warna kelas tutupan: Hutan (#14532d), Terbuka (#f59e0b), Kelapa (#2f9e44), Bangunan (#e8590c), Air (#1971c2)
    rgba[r_m[is_fst_m], c_m[is_fst_m]] = [20, 83, 45, 210]
    rgba[r_m[is_bare_m], c_m[is_bare_m]] = [245, 158, 11, 190]
    rgba[r_m[is_kel_m], c_m[is_kel_m]] = [47, 158, 68, 230]
    rgba[r_m[is_bld_m], c_m[is_bld_m]] = [232, 89, 12, 240]
    rgba[r_m[is_water_m], c_m[is_water_m]] = [25, 113, 194, 220]

    # 2. Tile 51MTP
    print("Memproses citra Sentinel-2 51MTP...")
    mtp_dir = Path("data/sentinel2_selayar/S2A_51MTP_20241007_0_L2A")
    with rasterio.open(mtp_dir / "SCL.tif") as src:
        r_box = box(*src.bounds)
        scl = src.read(1)
        scl_transform = src.transform
        scl_shape = src.shape
        crs = src.crs

    trans = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    sf = shapefile.Reader("Peta/Desa 7301/Desa_7301.shp")
    shapes = []
    for sr in sf.shapeRecords():
        g = transform(trans.transform, shape(sr.shape))
        if g.intersects(r_box):
            shapes.append((g.intersection(r_box), 1))

    admin_mask = features.rasterize(shapes, out_shape=scl_shape, transform=scl_transform, fill=0, dtype=np.uint8)
    valid_20m = (admin_mask == 1) & (scl != 6) & (scl != 0) & (~np.isin(scl, [3, 8, 9, 10]))
    valid_10m = np.repeat(np.repeat(valid_20m, 2, axis=0), 2, axis=1)
    r10, c10 = np.where(valid_10m)

    with rasterio.open(mtp_dir / "B04.tif") as src:
        b04_p = src.read(1)[r10, c10].astype(np.float32) * 1e-4
        trans_10m = src.transform
    with rasterio.open(mtp_dir / "B08.tif") as src:
        b08_p = src.read(1)[r10, c10].astype(np.float32) * 1e-4
    with rasterio.open(mtp_dir / "B02.tif") as src:
        b02_p = src.read(1)[r10, c10].astype(np.float32) * 1e-4
    with rasterio.open(mtp_dir / "B05.tif") as src:
        b05_p = src.read(1)[r10 // 2, c10 // 2].astype(np.float32) * 1e-4
    with rasterio.open(mtp_dir / "B11.tif") as src:
        b11_p = src.read(1)[r10 // 2, c10 // 2].astype(np.float32) * 1e-4

    eps = 1e-6
    ndvi_p = (b08_p - b04_p) / (b08_p + b04_p + eps)
    ndre1_p = (b08_p - b05_p) / (b08_p + b05_p + eps)
    bsi_p = ((b11_p + b04_p) - (b08_p + b02_p)) / ((b11_p + b04_p) + (b08_p + b02_p) + eps)
    ndwi_p = (b02_p - b08_p) / (b02_p + b08_p + eps)

    is_water_p = (scl[r10 // 2, c10 // 2] == 6) | ((ndwi_p > 0.05) & (b08_p < 0.12))
    is_bld_p = (~is_water_p) & (bsi_p > -0.05) & (ndvi_p < 0.32) & (b04_p > 0.08)
    is_kel_p = (~is_water_p) & (~is_bld_p) & (
        (ndvi_p >= 0.45) & (ndvi_p <= 0.88) &
        (ndre1_p >= 0.22) & (ndre1_p <= 0.65) &
        (b11_p <= 0.25) &
        (bsi_p < -0.10)
    )
    is_fst_p = (~is_water_p) & (~is_bld_p) & (~is_kel_p) & (ndvi_p >= 0.40)
    is_bare_p = (~is_water_p) & (~is_bld_p) & (~is_kel_p) & (~is_fst_p)

    x_utm_p = trans_10m.c + c10 * trans_10m.a
    y_utm_p = trans_10m.f + r10 * trans_10m.e

    c_p = np.clip(np.round((x_utm_p - x_min) / res).astype(np.int32), 0, w_grid - 1)
    r_p = np.clip(np.round((y_max - y_utm_p) / res).astype(np.int32), 0, h_grid - 1)

    rgba[r_p[is_fst_p], c_p[is_fst_p]] = [20, 83, 45, 210]
    rgba[r_p[is_bare_p], c_p[is_bare_p]] = [245, 158, 11, 190]
    rgba[r_p[is_kel_p], c_p[is_kel_p]] = [47, 158, 68, 230]
    rgba[r_p[is_bld_p], c_p[is_bld_p]] = [232, 89, 12, 240]
    rgba[r_p[is_water_p], c_p[is_water_p]] = [25, 113, 194, 220]

    # 3. Reproyeksi ke EPSG:4326 untuk keselarasan 100% pada Leaflet ImageOverlay
    print("Mereproyeksi ke EPSG:4326 (WGS84)...")
    src_crs = "EPSG:32751"
    dst_crs = "EPSG:4326"
    src_transform = rasterio.transform.from_bounds(x_min, y_min, x_max, y_max, w_grid, h_grid)

    dst_transform, dst_w, dst_h = calculate_default_transform(
        src_crs, dst_crs, w_grid, h_grid, left=x_min, bottom=y_min, right=x_max, top=y_max
    )

    dst_rgba = np.zeros((dst_h, dst_w, 4), dtype=np.uint8)
    for ch in range(4):
        reproject(
            source=rgba[:, :, ch],
            destination=dst_rgba[:, :, ch],
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
        )

    out_img = Image.fromarray(dst_rgba, "RGBA")
    out_img.save(out_png, optimize=True)
    if dist_dir.exists():
        out_img.save(dist_dir / "segmentasi_selayar.png", optimize=True)

    min_lon = dst_transform.c
    max_lat = dst_transform.f
    max_lon = min_lon + dst_w * dst_transform.a
    min_lat = max_lat + dst_h * dst_transform.e

    print(f"SELESAI! Berkas disimpan: {out_png} ({out_png.stat().st_size / 1024:.1f} KB, resolusi {out_img.size})")
    print(f"Batas Geografis WGS84 Leaflet: [[{min_lat:.6f}, {min_lon:.6f}], [{max_lat:.6f}, {max_lon:.6f}]]")
    print(f"Total waktu komputasi: {time.time() - t0:.2f} detik")


if __name__ == "__main__":
    main()
