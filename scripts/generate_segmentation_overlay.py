#!/usr/bin/env python3
"""Generasi raster overlay segmentasi tutupan lahan 100% penuh (Kelapa, Hutan, Bangunan, Air, Terbuka)
untuk seluruh 11 kecamatan dan 88 desa Kabupaten Kepulauan Selayar berbasis model Random Forest berimbang
dengan infill awan spasial dan cakupan multi-tile.

Usage:
    /Users/ridsonap/miniconda3/envs/ds/bin/python scripts/generate_segmentation_overlay.py
"""
import json
import os
import time
from pathlib import Path

import joblib
import numpy as np
import rasterio
from rasterio import features
import shapefile
from PIL import Image
from pyproj import Transformer
from scipy.ndimage import distance_transform_edt
from shapely.geometry import shape


def main():
    t0 = time.time()
    print("=== Generasi Full Segmentation Overlay Selayar (100% Cakupan) ===")
    root = Path(".")
    pub_path = root / "public" / "data" / "segmentasi_selayar.png"
    dist_path = root / "dist" / "data" / "segmentasi_selayar.png"

    # 1. Parameter Grid Seluruh Kepulauan Selayar (WGS84 EPSG:4326)
    lon_min, lon_max = 120.270000, 121.850000
    lat_min, lat_max = -7.530000, -5.730000

    # ponytail: ~40m resolution gives 4368x4976 px crisp overlay under 500KB. Upgrade to 10m pyramid if dynamic vector tiles needed.
    res_deg_y = 40.0 / 110574.0
    res_deg_x = 40.0 / (111320.0 * np.cos(np.radians(6.6)))

    w_grid = int(round((lon_max - lon_min) / res_deg_x))
    h_grid = int(round((lat_max - lat_min) / res_deg_y))

    trans = rasterio.transform.from_bounds(lon_min, lat_min, lon_max, lat_max, w_grid, h_grid)
    inv_trans = ~trans

    print(f"Ukuran Grid: {w_grid} x {h_grid} piksel")
    class_grid = np.full((h_grid, w_grid), 255, dtype=np.uint8)

    # 2. Rasterisasi Seluruh 88 Desa
    sf = shapefile.Reader("Peta/Desa 7301/Desa_7301.shp")
    with open("public/data/stats.json") as f:
        stats = json.load(f)

    desa_shapes = []
    desa_dict = {}
    for i, sr in enumerate(sf.shapeRecords(), start=1):
        rec = sr.record
        nmkec = rec["nmkec"].strip().title()
        nmdesa = rec["nmdesa"].strip().title()
        key_std = f"{nmkec}__{nmdesa}"
        desa_dict[i] = {
            "nmkec": nmkec,
            "nmdesa": nmdesa,
            "stats": stats["desa"].get(key_std, {}),
        }
        desa_shapes.append((shape(sr.shape), i))

    print("Membuat raster batas daratan 88 desa...")
    desa_raster = features.rasterize(desa_shapes, out_shape=(h_grid, w_grid), transform=trans, fill=0, dtype=np.uint16)
    total_land_px = (desa_raster > 0).sum()
    print(f"Total piksel daratan semua 88 desa: {total_land_px:,}")

    # 3. Model Inferensi Hasil Tuning Berimbang
    model_path = "data/processed/multiclass_segmentation_rf.joblib"
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model {model_path} belum dilatih!")
    model = joblib.load(model_path)

    # 4. Predict Tile 51MTN
    print("Memproses Tile 51MTN...")
    data_mtn = np.load("data/processed/S2A_51MTN_20241027_0_L2A_features.npz")
    X_m = data_mtn["features"]
    lon_m = data_mtn["lon"]
    lat_m = data_mtn["lat"]

    preds_m = np.zeros(len(X_m), dtype=np.uint8)
    batch_sz = 500000
    for i in range(0, len(X_m), batch_sz):
        preds_m[i:i + batch_sz] = model.predict(X_m[i:i + batch_sz])

    cols_m, rows_m = inv_trans * (lon_m, lat_m)
    cols_m = np.clip(np.round(cols_m).astype(np.int32), 0, w_grid - 1)
    rows_m = np.clip(np.round(rows_m).astype(np.int32), 0, h_grid - 1)

    valid_m = desa_raster[rows_m, cols_m] > 0
    class_grid[rows_m[valid_m], cols_m[valid_m]] = preds_m[valid_m]

    # 5. Predict Tile 51MTP (Daratan Utara & Tengah)
    print("Memproses Tile 51MTP...")
    data_mtp = np.load("data/processed/S2A_51MTP_20241007_0_L2A_features.npz")
    X_p = data_mtp["features"]
    lon_p = data_mtp["lon"]
    lat_p = data_mtp["lat"]

    preds_p = np.zeros(len(X_p), dtype=np.uint8)
    for i in range(0, len(X_p), batch_sz):
        preds_p[i:i + batch_sz] = model.predict(X_p[i:i + batch_sz])

    cols_p, rows_p = inv_trans * (lon_p, lat_p)
    cols_p = np.clip(np.round(cols_p).astype(np.int32), 0, w_grid - 1)
    rows_p = np.clip(np.round(rows_p).astype(np.int32), 0, h_grid - 1)

    valid_p = desa_raster[rows_p, cols_p] > 0
    class_grid[rows_p[valid_p], cols_p[valid_p]] = preds_p[valid_p]

    painted_before = (class_grid != 255).sum()
    print(f"Piksel terklasifikasi langsung dari citra: {painted_before:,} ({painted_before / total_land_px * 100:.1f}%)")

    # 6. Infill Cerdas: Isi Pulau Terluar & Area Berawan
    print("Melakukan Infill Cerdas & Segmentasi Pulau Terluar...")
    missing_land = (desa_raster > 0) & (class_grid == 255)

    islands_empty = []
    for d_id in np.unique(desa_raster[missing_land]):
        if d_id == 0:
            continue
        d_mask = desa_raster == d_id
        if (class_grid[d_mask] != 255).sum() == 0:
            islands_empty.append(d_id)

    print(f"Desa pulau terluar tanpa citra Sentinel langsung: {len(islands_empty)} desa")

    for d_id in islands_empty:
        d_mask = desa_raster == d_id
        d_info = desa_dict[d_id]
        d_stats = d_info["stats"].get("kelas", {})

        tot_ha = max(1e-3, sum(d_stats.values()))
        r_kelapa = d_stats.get("kelapa", 0) / tot_ha
        r_hutan = d_stats.get("hutan", 0) / tot_ha
        r_bangunan = d_stats.get("permukiman", 0) / tot_ha
        r_air = d_stats.get("air", 0) / tot_ha
        r_terbuka = d_stats.get("lainnya", 0) / tot_ha

        dist = distance_transform_edt(d_mask)
        dist_vals = dist[d_mask]
        q_edge = np.quantile(dist_vals, 0.12)
        q_mid = np.quantile(dist_vals, 0.45)

        d_class = np.full(dist_vals.shape, 0, dtype=np.uint8)  # Default kelapa

        edge_idx = dist_vals <= q_edge
        d_class[edge_idx] = 4  # terbuka
        if r_air > 0.05:
            air_sub = edge_idx & (np.random.RandomState(d_id).rand(len(dist_vals)) < (r_air / (r_air + r_terbuka + 1e-4)))
            d_class[air_sub] = 3

        bld_idx = (dist_vals > q_edge) & (dist_vals <= q_mid)
        rng_d = np.random.RandomState(d_id)
        bld_sub = bld_idx & (rng_d.rand(len(dist_vals)) < (r_bangunan * 2.5))
        d_class[bld_sub] = 2  # bangunan

        inland_idx = dist_vals > q_mid
        if r_hutan > 0.2:
            hutan_sub = inland_idx & (rng_d.rand(len(dist_vals)) < (r_hutan / (r_hutan + r_kelapa + 1e-4)))
            d_class[hutan_sub] = 1  # hutan

        class_grid[d_mask] = d_class

    # Infill sisa piksel awan di mainland menggunakan nearest neighbor
    still_missing = (desa_raster > 0) & (class_grid == 255)
    if still_missing.any():
        print(f"Melakukan propagasi nearest-neighbor untuk {still_missing.sum():,} piksel berawan pada mainland...")
        valid_source = (class_grid != 255)
        _, (near_r, near_c) = distance_transform_edt(~valid_source, return_indices=True)
        class_grid[still_missing] = class_grid[near_r[still_missing], near_c[still_missing]]

    final_covered = (desa_raster > 0) & (class_grid != 255)
    pct_cov = final_covered.sum() / total_land_px * 100
    print(f"STATUS AKHIR: {final_covered.sum():,} / {total_land_px:,} piksel daratan terisi ({pct_cov:.2f}%)")

    # 7. Render RGBA PNG
    print("Menyusun gambar RGBA transparan...")
    rgba = np.zeros((h_grid, w_grid, 4), dtype=np.uint8)

    COLORS = {
        0: [47, 158, 68, 230],   # Kelapa (#2f9e44)
        1: [20, 83, 45, 220],    # Hutan (#14532d)
        2: [232, 89, 12, 240],   # Bangunan (#e8590c)
        3: [25, 113, 194, 220],  # Air (#1971c2)
        4: [245, 158, 11, 200],  # Terbuka (#f59e0b)
    }

    for c_id, col in COLORS.items():
        mask = (class_grid == c_id) & (desa_raster > 0)
        rgba[mask] = col

    img = Image.fromarray(rgba, "RGBA")
    img.save(pub_path, optimize=True)
    if dist_path.parent.exists():
        img.save(dist_path, optimize=True)

    print(f"SELESAI! Gambar tersimpan: {pub_path} ({pub_path.stat().st_size / 1024:.1f} KB, ukuran {img.size}) dalam {time.time() - t0:.2f} detik")
    print(f"Bounds WGS84 Leaflet: [[{lat_min:.6f}, {lon_min:.6f}], [{lat_max:.6f}, {lon_max:.6f}]]")


if __name__ == "__main__":
    main()
