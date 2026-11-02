#!/usr/bin/env python3
"""Download Sentinel-2 L2A bands for Kepulauan Selayar via AWS Open Data.
No credentials or third-party packages required (pure Python stdlib).

Usage:
    python3 scripts/download_sentinel2.py --tile 51MTN --bands B04,B08,B05,B11
    python3 scripts/download_sentinel2.py --tile 51MTN --all-bands
    python3 scripts/download_sentinel2.py --list
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

STAC_URL = "https://earth-search.aws.element84.com/v1/search"
OUT_DIR_DEFAULT = Path("data/sentinel2_selayar")

# Band-band yang krusial untuk klasifikasi kelapa
ESSENTIAL_BANDS = ["B02", "B03", "B04", "B08", "B05", "B06", "B07", "B8A", "B11", "B12", "SCL"]


def search_scenes(tile="51MTN", date_range="2024-07-01T00:00:00Z/2024-11-01T23:59:59Z", max_cloud=5, limit=3):
    """Cari scene Sentinel-2 L2A bebas awan di AWS Earth Search."""
    payload = {
        "collections": ["sentinel-2-l2a"],
        "query": {
            "grid:code": {"eq": f"MGRS-{tile}"},
            "eo:cloud_cover": {"lt": max_cloud},
        },
        "datetime": date_range,
        "limit": limit,
    }
    req = urllib.request.Request(
        STAC_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "gemerlap/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def download_file(url, out_path, chunk_size=1024 * 1024):
    """Download single file dengan progress display."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        # Cek apakah file sudah lengkap
        req_head = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "gemerlap/1.0"})
        try:
            with urllib.request.urlopen(req_head, timeout=15) as rhead:
                remote_size = int(rhead.headers.get("Content-Length", 0))
                if remote_size > 0 and out_path.stat().st_size == remote_size:
                    print(f"  [OK - Already exists] {out_path.name} ({remote_size/(1024*1024):.1f} MB)")
                    return
        except Exception:
            pass

    req = urllib.request.Request(url, headers={"User-Agent": "gemerlap/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(out_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded / total * 100
                    mb_down = downloaded / (1024 * 1024)
                    mb_tot = total / (1024 * 1024)
                    sys.stdout.write(f"\r  Downloading {out_path.name}: {mb_down:.1f}/{mb_tot:.1f} MB ({pct:.1f}%)")
                    sys.stdout.flush()
        sys.stdout.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Download Sentinel-2 L2A untuk Selayar (AWS Open Data)")
    parser.add_argument("--tile", default="51MTN", choices=["51MTN", "51MTP"], help="Tile MGRS (51MTN = Selayar Selatan/Benteng, 51MTP = Selayar Utara)")
    parser.add_argument("--bands", default="B04,B08,B05,B11,SCL", help="Band dipisah koma (contoh: B02,B03,B04,B08,B05,B06,B07,B11,B12,SCL)")
    parser.add_argument("--all-bands", action="store_true", help="Download semua 11 band esensial")
    parser.add_argument("--list", action="store_true", help="Hanya tampilkan daftar scene yang tersedia")
    parser.add_argument("--outdir", default=str(OUT_DIR_DEFAULT), help="Folder output")

    args = parser.parse_args()

    print(f"Mencari scene bebas awan untuk MGRS-{args.tile}...")
    res = search_scenes(tile=args.tile)
    features = res.get("features", [])

    if not features:
        print("Tidak ada scene yang cocok.")
        return

    print(f"Ditemukan {len(features)} scene terbaik:")
    for idx, f in enumerate(features):
        p = f["properties"]
        print(f"  [{idx+1}] {f['id']} | Tanggal: {p['datetime'][:10]} | Awan: {p.get('eo:cloud_cover', 0):.2f}%")

    if args.list:
        return

    best_scene = features[0]
    scene_id = best_scene["id"]
    print(f"\nMemilih scene terbaik: {scene_id}")

    bands_to_download = ESSENTIAL_BANDS if args.all_bands else [b.strip() for b in args.bands.split(",")]
    out_dir = Path(args.outdir) / scene_id
    out_dir.mkdir(parents=True, exist_ok=True)

    base_s3_url = f"https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/{args.tile[:2]}/{args.tile[2]}/{args.tile[3:]}/{best_scene['properties']['datetime'][:4]}/{best_scene['properties']['datetime'][5:7]}/{scene_id}/"

    print(f"Menyimpan ke: {out_dir}")
    print(f"Band yang diunduh: {', '.join(bands_to_download)}\n")

    for band in bands_to_download:
        filename = f"{band}.tif"
        url = base_s3_url + filename
        out_file = out_dir / filename
        try:
            download_file(url, out_file)
        except Exception as e:
            print(f"  Gagal unduh {band}: {e}")

    print("\nSelesai! Berkas siap digunakan untuk klasifikasi.")


if __name__ == "__main__":
    main()
