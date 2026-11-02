#!/usr/bin/env python3
"""Pipeline perhitungan indeks spektral, crop & masking batas administrasi,
serta ekstraksi fitur citra Sentinel-2 L2A untuk klasifikasi pohon kelapa.

Usage:
    /Users/ridsonap/miniconda3/envs/ds/bin/python scripts/process_sentinel2.py \
        --scene-dir data/sentinel2_selayar/S2A_51MTN_20241027_0_L2A \
        --shapefile "Peta/Desa 7301/Desa_7301.shp" \
        --out-dir data/processed
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio import features
import shapefile
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform


def load_admin_shapes(shp_path, target_box, target_crs):
    """Load and reproject administrative shapes intersecting target raster box."""
    sf = shapefile.Reader(shp_path)
    # Target CRS is typically UTM Zone 51S (EPSG:32751)
    trans = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)

    shapes_list = []
    desa_records = {}
    desa_idx = 1

    for sr in sf.shapeRecords():
        # ponytail: unary shape transform. Upgrade to vectorized shapely.transform if >10k polygons.
        g = transform(trans.transform, shape(sr.shape))
        if g.intersects(target_box):
            inter_g = g.intersection(target_box)
            shapes_list.append((inter_g, desa_idx))
            rec = sr.record
            desa_records[desa_idx] = {
                "id": desa_idx,
                "nmkec": str(rec["nmkec"]).strip(),
                "nmdesa": str(rec["nmdesa"]).strip(),
                "kddesa": str(rec["kddesa"]).strip(),
            }
            desa_idx += 1

    return shapes_list, desa_records


def main():
    parser = argparse.ArgumentParser(description="Crop, Masking, & Ekstraksi Fitur Sentinel-2 Selayar")
    parser.add_argument("--scene-dir", default="data/sentinel2_selayar/S2A_51MTN_20241027_0_L2A")
    parser.add_argument("--shapefile", default="Peta/Desa 7301/Desa_7301.shp")
    parser.add_argument("--out-dir", default="data/processed")
    parser.add_argument("--no-geotiff", action="store_true", help="Lewati penulisan GeoTIFF")
    args = parser.parse_args()

    scene_path = Path(args.scene_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene_id = scene_path.name
    t_start = time.time()

    print(f"=== Memulai Pemrosesan Sentinel-2: {scene_id} ===")
    scl_path = scene_path / "SCL.tif"
    if not scl_path.exists():
        sys.exit(f"File SCL.tif tidak ditemukan di {scene_path}")

    # 1. Buka SCL (20m) untuk batas geospasial & masking kualitas
    with rasterio.open(scl_path) as scl_src:
        r_box = box(*scl_src.bounds)
        scl = scl_src.read(1)
        scl_transform = scl_src.transform
        scl_crs = scl_src.crs
        scl_shape = scl_src.shape

    print(f"Raster SCL loaded ({scl_shape[1]}x{scl_shape[0]} piksel pada CRS {scl_crs})")

    # 2. Rasterize batas administrasi desa
    print("Memuat dan memotong batas administrasi desa...")
    shapes_list, desa_records = load_admin_shapes(args.shapefile, r_box, scl_crs)
    print(f"Ditemukan {len(shapes_list)} desa/kelurahan yang beririsan dengan scene ini.")

    admin_raster = features.rasterize(
        shapes_list, out_shape=scl_shape, transform=scl_transform, fill=0, dtype=np.uint16
    )

    # 3. Masking: Daratan dalam batas administrasi, non-air (6), non-awan (3, 8, 9, 10), non-nodata (0)
    # ponytail: hardcoded SCL classes for land & non-cloud. Upgrade to configurable list if custom masks required.
    valid_mask_20m = (admin_raster > 0) & (scl != 6) & (scl != 0) & (~np.isin(scl, [3, 8, 9, 10]))
    valid_mask_10m = np.repeat(np.repeat(valid_mask_20m, 2, axis=0), 2, axis=1)

    r10, c10 = np.where(valid_mask_10m)
    n_pixels = len(r10)
    print(f"Piksel daratan valid bebas awan pada grid 10m: {n_pixels:,} piksel ({n_pixels * 0.01:,.1f} ha)")

    if n_pixels == 0:
        sys.exit("Tidak ada piksel valid untuk diekstraksi.")

    # 4. Koordinat piksel
    # Transform row/col 10m ke UTM 51S (x, y) lalu WGS84 (lon, lat)
    # Coordinate of pixel center:
    x_utm = scl_src.bounds.left + (c10 * 10.0) + 5.0
    y_utm = scl_src.bounds.top - (r10 * 10.0) - 5.0

    print("Mengonversi koordinat UTM ke WGS84...")
    trans_wgs84 = Transformer.from_crs(scl_crs, "EPSG:4326", always_xy=True)
    lons, lats = trans_wgs84.transform(x_utm, y_utm)

    # Ambil ID desa untuk masing-masing piksel
    pixel_desa_ids = admin_raster[r10 // 2, c10 // 2]

    # 5. Ekstraksi Band 10m (B02, B03, B04, B08)
    print("Mengekstraksi band resolusi 10m (B02, B03, B04, B08)...")
    bands_10m = {}
    for b in ["B02", "B03", "B04", "B08"]:
        b_file = scene_path / f"{b}.tif"
        if not b_file.exists():
            sys.exit(f"Band {b} tidak ditemukan di {scene_path}")
        with rasterio.open(b_file) as src:
            # Baca hanya piksel yang valid langsung ke 1D array
            bands_10m[b] = src.read(1)[r10, c10].astype(np.float32) * 1e-4

    # 6. Ekstraksi Band 20m (B05, B06, B07, B8A, B11, B12)
    # ponytail: 20m bands upsampled to 10m via index mapping (r10//2, c10//2). Upgrade to bilinear if sub-pixel interpolation is needed.
    print("Mengekstraksi band resolusi 20m (B05, B06, B07, B8A, B11, B12)...")
    bands_20m = {}
    for b in ["B05", "B06", "B07", "B8A", "B11", "B12"]:
        b_file = scene_path / f"{b}.tif"
        if not b_file.exists():
            sys.exit(f"Band {b} tidak ditemukan di {scene_path}")
        with rasterio.open(b_file) as src:
            bands_20m[b] = src.read(1)[r10 // 2, c10 // 2].astype(np.float32) * 1e-4

    # 7. Perhitungan Indeks Spektral
    print("Menghitung indeks vegetasi & spektral kelapa (NDVI, NDRE1, NDRE2, NDWI, MNDWI, BSI, EVI, NBR2)...")
    b02, b03, b04, b08 = bands_10m["B02"], bands_10m["B03"], bands_10m["B04"], bands_10m["B08"]
    b05, b06, b07 = bands_20m["B05"], bands_20m["B06"], bands_20m["B07"]
    b8a, b11, b12 = bands_20m["B8A"], bands_20m["B11"], bands_20m["B12"]

    eps = 1e-6
    ndvi = (b08 - b04) / (b08 + b04 + eps)
    ndre1 = (b08 - b05) / (b08 + b05 + eps)
    ndre2 = (b08 - b06) / (b08 + b06 + eps)
    ndwi = (b03 - b08) / (b03 + b08 + eps)
    mndwi = (b03 - b11) / (b03 + b11 + eps)
    bsi = ((b11 + b04) - (b08 + b02)) / ((b11 + b04) + (b08 + b02) + eps)
    evi = 2.5 * (b08 - b04) / (b08 + 6.0 * b04 - 7.5 * b02 + 1.0 + eps)
    nbr2 = (b11 - b12) / (b11 + b12 + eps)

    # 8. Baseline heuristic / filtering kandidat kelapa
    # ponytail: heuristic coconut threshold baseline. Upgrade to trained RF/LightGBM model when ground-truth points are loaded.
    is_vegetation = ndvi >= 0.3
    is_coconut_candidate = (
        (ndvi >= 0.45) & (ndvi <= 0.88) &
        (ndre1 >= 0.22) & (ndre1 <= 0.65) &
        (b11 <= 0.25) & (b12 <= 0.20) &
        (bsi < -0.10)
    )

    veg_count = int(is_vegetation.sum())
    coconut_count = int(is_coconut_candidate.sum())
    print(f"Hasil Klasifikasi Awal:")
    print(f"  Total Vegetasi (NDVI >= 0.3)     : {veg_count:,} piksel ({veg_count * 0.01:,.1f} ha)")
    print(f"  Kandidat Kelapa Spektral (Rule) : {coconut_count:,} piksel ({coconut_count * 0.01:,.1f} ha)")

    # 9. Rekapitulasi per Desa
    print("Menyusun ringkasan statistik per desa...")
    desa_summary = {}
    for d_id, rec in desa_records.items():
        mask_d = pixel_desa_ids == d_id
        count_d = int(mask_d.sum())
        if count_d == 0:
            continue
        veg_d = int(is_vegetation[mask_d].sum())
        coco_d = int(is_coconut_candidate[mask_d].sum())
        ndvi_sub = ndvi[mask_d]
        ndre_sub = ndre1[mask_d]
        bsi_sub = bsi[mask_d]

        key = f"{rec['nmkec']}__{rec['nmdesa']}"
        desa_summary[key] = {
            "nmkec": rec["nmkec"],
            "nmdesa": rec["nmdesa"],
            "kddesa": rec["kddesa"],
            "total_land_pixels": count_d,
            "total_land_ha": round(count_d * 0.01, 1),
            "vegetation_ha": round(veg_d * 0.01, 1),
            "coconut_candidate_ha": round(coco_d * 0.01, 1),
            "coconut_ratio_pct": round(coco_d / max(count_d, 1) * 100, 1),
            "mean_ndvi": round(float(np.mean(ndvi_sub)), 3),
            "mean_ndre1": round(float(np.mean(ndre_sub)), 3),
            "mean_bsi": round(float(np.mean(bsi_sub)), 3),
        }

    summary_file = out_dir / f"{scene_id}_desa_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(desa_summary, f, indent=2)
    print(f"Disimpan ringkasan statistik: {summary_file}")

    # 10. Simpan dataset fitur piksel lengkap (NPZ)
    feature_matrix = np.column_stack([
        b02, b03, b04, b08,
        b05, b06, b07, b8a, b11, b12,
        ndvi, ndre1, ndre2, ndwi, mndwi, bsi, evi, nbr2
    ]).astype(np.float32)

    feature_names = [
        "B02", "B03", "B04", "B08",
        "B05", "B06", "B07", "B8A", "B11", "B12",
        "NDVI", "NDRE1", "NDRE2", "NDWI", "MNDWI", "BSI", "EVI", "NBR2"
    ]

    npz_file = out_dir / f"{scene_id}_features.npz"
    np.savez_compressed(
        npz_file,
        features=feature_matrix,
        feature_names=np.array(feature_names),
        x_utm=x_utm.astype(np.float32),
        y_utm=y_utm.astype(np.float32),
        lon=lons.astype(np.float32),
        lat=lats.astype(np.float32),
        desa_id=pixel_desa_ids.astype(np.uint16),
        is_vegetation=is_vegetation,
        is_coconut_candidate=is_coconut_candidate,
    )
    print(f"Disimpan feature dataset: {npz_file} ({npz_file.stat().st_size / (1024*1024):.1f} MB)")

    # 11. GeoTIFF Indeks Spektral (Opsional tapi sangat berguna untuk visualisasi GIS)
    if not args.no_geotiff:
        print("Menulis GeoTIFF indeks spektral kompresi DEFLATE (NDVI, NDRE1, NDWI, BSI)...")
        # Bounds daratan yang beririsan
        r_min, r_max = int(r10.min()), int(r10.max())
        c_min, c_max = int(c10.min()), int(c10.max())
        crop_h = r_max - r_min + 1
        crop_w = c_max - c_min + 1

        crop_transform = rasterio.transform.from_origin(
            scl_src.bounds.left + c_min * 10.0,
            scl_src.bounds.top - r_min * 10.0,
            10.0, 10.0
        )

        tif_profile = {
            "driver": "GTiff",
            "height": crop_h,
            "width": crop_w,
            "count": 4,
            "dtype": "float32",
            "crs": scl_crs,
            "transform": crop_transform,
            "compress": "deflate",
            "nodata": -9999.0,
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
        }

        indices_tif = out_dir / f"{scene_id}_indices.tif"
        with rasterio.open(indices_tif, "w", **tif_profile) as dst:
            dst.set_band_description(1, "NDVI")
            dst.set_band_description(2, "NDRE1")
            dst.set_band_description(3, "NDWI")
            dst.set_band_description(4, "BSI")

            # Inisialisasi nodata buffer per band
            local_r = r10 - r_min
            local_c = c10 - c_min
            for b_idx, arr_data in enumerate([ndvi, ndre1, ndwi, bsi], start=1):
                band_buf = np.full((crop_h, crop_w), -9999.0, dtype=np.float32)
                band_buf[local_r, local_c] = arr_data
                dst.write(band_buf, b_idx)

        print(f"Disimpan GeoTIFF indeks: {indices_tif} ({indices_tif.stat().st_size / (1024*1024):.1f} MB)")

    duration = time.time() - t_start
    print(f"\n=== Selesai dalam {duration:.1f} detik! ===")


if __name__ == "__main__":
    main()
