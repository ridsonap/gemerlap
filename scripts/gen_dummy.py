"""Generate GeoJSON desa/kecamatan + dummy stats klasifikasi.
Input : Peta/Desa 7301/Desa_7301.shp, Peta/Kec 7301/kec_7301.shp
Output: public/data/desa.geojson, kecamatan.geojson, stats.json, classes.json
Dummy, deterministik (seed tetap) agar stabil antar build.
"""
import json, math, os, random
from pathlib import Path

try:
    import shapefile  # pyshp
except ImportError:
    raise SystemExit("pip install pyshp  (pip install --break-system-packages pyshp)")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "data"
OUT.mkdir(parents=True, exist_ok=True)

CLASSES = [
    {"id": "kelapa",     "label": "Kelapa",     "color": "#2f9e44"},
    {"id": "pala",       "label": "Pala",       "color": "#8c5a2b"},
    {"id": "cengkeh",    "label": "Cengkeh",    "color": "#7048e8"},
    {"id": "jagung",     "label": "Jagung",     "color": "#f08c00"},
    {"id": "padi",       "label": "Padi",       "color": "#94d82d"},
    {"id": "hutan",      "label": "Hutan/Mangrove", "color": "#14532d"},
    {"id": "permukiman", "label": "Permukiman", "color": "#e8590c"},
    {"id": "air",        "label": "Air",        "color": "#1971c2"},
    {"id": "lainnya",    "label": "Lainnya",    "color": "#adb5bd"},
]

# Bobot dasar per kecamatan supaya pola dummy terlihat realistis
KEC_PROFILE = {
    "BONTOMANAI":      {"kelapa": 30, "pala": 6,  "cengkeh": 8,  "jagung": 12, "padi": 14},
    "BONTOMATENE":     {"kelapa": 26, "pala": 8,  "cengkeh": 10, "jagung": 10, "padi": 12},
    "BONTOSIKUYU":     {"kelapa": 22, "pala": 10, "cengkeh": 16, "jagung": 8,  "padi": 10},
    "BONTOHARU":       {"kelapa": 28, "pala": 5,  "cengkeh": 6,  "jagung": 9,  "padi": 8},
    "BENTENG":         {"kelapa": 10, "pala": 2,  "cengkeh": 2,  "jagung": 4,  "padi": 4},
    "BUKI":            {"kelapa": 24, "pala": 7,  "cengkeh": 9,  "jagung": 11, "padi": 13},
    "PASILAMBENA":     {"kelapa": 32, "pala": 4,  "cengkeh": 3,  "jagung": 6,  "padi": 2},
    "PASIMARANNU":     {"kelapa": 30, "pala": 3,  "cengkeh": 3,  "jagung": 5,  "padi": 2},
    "PASIMASSUNGGU":   {"kelapa": 31, "pala": 3,  "cengkeh": 3,  "jagung": 5,  "padi": 2},
    "PASIMASSUNGGU TIMUR": {"kelapa": 29, "pala": 3, "cengkeh": 3, "jagung": 5, "padi": 2},
    "TAKABONERATE":    {"kelapa": 20, "pala": 1,  "cengkeh": 1,  "jagung": 2,  "padi": 1},
}
BASE_OTHER = {"hutan": 14, "permukiman": 4, "air": 5, "lainnya": 6}


def r5(x):
    return round(float(x), 5)


def thin_ring(pts, max_pts=400):
    """Decimate ring agar file ringan (dummy). Pertahankan titik pertama/terakhir."""
    if len(pts) <= max_pts:
        return [[r5(x), r5(y)] for x, y in pts]
    step = math.ceil(len(pts) / max_pts)
    kept = pts[::step]
    if kept[-1] != pts[-1]:
        kept = kept + [pts[-1]]
    return [[r5(x), r5(y)] for x, y in kept]


def shp_to_geojson(shp_path, level):
    r = shapefile.Reader(str(shp_path), encoding="utf-8", errors="ignore")
    # field names
    fields = [f[0] for f in r.fields[1:]]
    feats = []
    for sr in r.iterShapeRecords():
        rec = dict(zip(fields, sr.record))
        shp = sr.shape
        if shp.shapeTypeName not in ("POLYGON", "POLYGONZ", "POLYGONM"):
            continue
        # split parts into rings
        pts = shp.points
        parts = list(shp.parts) + [len(pts)]
        rings = []
        for i in range(len(parts) - 1):
            ring = pts[parts[i]:parts[i + 1]]
            if len(ring) >= 4:
                rings.append(thin_ring(ring))
        if not rings:
            continue
        nmkec = (rec.get("nmkec") or "").strip()
        nmdesa = (rec.get("nmdesa") or "").strip()
        kdkec = (rec.get("kdkec") or "").strip()
        kddesa = (rec.get("kddesa") or "").strip()
        if level == "desa":
            fid = f"{kdkec}.{kddesa}.{nmdesa}".replace(" ", "_")
            props = {"id": fid, "nmkec": nmkec.title(), "nmdesa": nmdesa.title(),
                     "kdkec": kdkec, "kddesa": kddesa}
        else:
            props = {"id": kdkec, "nmkec": nmkec.title(), "kdkec": kdkec}
        feats.append({"type": "Feature", "properties": props,
                      "geometry": {"type": "Polygon" if len(rings) == 1 else "MultiPolygon",
                                   "coordinates": [rings[0]] if len(rings) == 1 else [[r] for r in rings]}})
    # gabung feature kecamatan dgn nmkec sama (jaga2 kalau shp belum dissolve)
    if level == "kecamatan":
        by_kec = {}
        for f in feats:
            by_kec.setdefault(f["properties"]["nmkec"], []).append(f)
        merged = []
        for nmkec, fs in by_kec.items():
            if len(fs) == 1:
                merged.append(fs[0])
                continue
            coords = []
            for f in fs:
                g = f["geometry"]
                if g["type"] == "Polygon":
                    coords.append(g["coordinates"])
                else:
                    coords.extend(g["coordinates"])
            merged.append({"type": "Feature", "properties": fs[0]["properties"],
                           "geometry": {"type": "MultiPolygon", "coordinates": coords}})
        feats = merged
    return {"type": "FeatureCollection", "features": feats}


def gen_stats(desa_fc):
    rnd = random.Random(42)
    desa_stats, kec_agg, kab = {}, {}, {c["id"]: 0.0 for c in CLASSES}
    for f in desa_fc["features"]:
        p = f["properties"]
        nmkec_up = p["nmkec"].upper()
        prof = dict(KEC_PROFILE.get(nmkec_up, {"kelapa": 25, "pala": 5, "cengkeh": 6, "jagung": 8, "padi": 8}))
        prof.update(BASE_OTHER)
        # variasi acak ±35%
        w = {k: v * rnd.uniform(0.65, 1.35) for k, v in prof.items()}
        total = rnd.uniform(250, 2600)  # Ha per desa (dummy)
        s = sum(w.values())
        luas = {k: round(total * v / s, 1) for k, v in w.items()}
        # koreksi rounding
        diff = round(total - sum(luas.values()), 1)
        luas[max(luas, key=luas.get)] = round(luas[max(luas, key=luas.get)] + diff, 1)
        dom = max(["kelapa", "pala", "cengkeh", "jagung", "padi"], key=lambda k: luas[k])
        key = f"{p['nmkec']}__{p['nmdesa']}"
        desa_stats[key] = {"nmkec": p["nmkec"], "nmdesa": p["nmdesa"],
                           "total_ha": round(total, 1), "dominan": dom, "kelas": luas}
        p["dominan"] = dom
        p["total_ha"] = round(total, 1)
        ka = kec_agg.setdefault(p["nmkec"], {"total_ha": 0.0, "kelas": {c["id"]: 0.0 for c in CLASSES}, "n_desa": 0})
        ka["n_desa"] += 1
        ka["total_ha"] += total
        for k, v in luas.items():
            ka["kelas"][k] += v
            kab[k] += v
    for ka in kec_agg.values():
        ka["total_ha"] = round(ka["total_ha"], 1)
        ka["kelas"] = {k: round(v, 1) for k, v in ka["kelas"].items()}
        fokus = ["kelapa", "pala", "cengkeh", "jagung", "padi"]
        ka["dominan"] = max(fokus, key=lambda k: ka["kelas"][k])
    kab = {k: round(v, 1) for k, v in kab.items()}
    return desa_stats, kec_agg, kab


def main():
    desa_fc = shp_to_geojson(ROOT / "Peta" / "Desa 7301" / "Desa_7301.shp", "desa")
    kec_fc = shp_to_geojson(ROOT / "Peta" / "Kec 7301" / "kec_7301.shp", "kecamatan")
    print(f"desa: {len(desa_fc['features'])} fitur, kec: {len(kec_fc['features'])} fitur")
    desa_stats, kec_agg, kab = gen_stats(desa_fc)
    (OUT / "desa.geojson").write_text(json.dumps(desa_fc), encoding="utf-8")
    (OUT / "kecamatan.geojson").write_text(json.dumps(kec_fc), encoding="utf-8")
    (OUT / "classes.json").write_text(json.dumps(CLASSES, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "stats.json").write_text(json.dumps(
        {"meta": {"sumber": "DUMMY — ganti dengan hasil klasifikasi Sentinel-2",
                  "satuan": "hektar (ha)", "tahun": 2025, "catatan": "Angka acak deterministik untuk prototipe UI"},
         "kelas": CLASSES, "kabupaten": {"total_ha": round(sum(kab.values()), 1), "kelas": kab},
         "kecamatan": kec_agg, "desa": desa_stats},
        ensure_ascii=False), encoding="utf-8")
    print("ditulis ke public/data/ (desa, kecamatan, stats, classes)")


if __name__ == "__main__":
    main()
