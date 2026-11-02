#!/usr/bin/env python3
"""Pelatihan beberapa model machine learning (LightGBM, Random Forest, Logistic Regression, GaussianNB)
dan inferensi spasial tutupan pohon kelapa untuk Kepulauan Selayar.

Usage:
    /Users/ridsonap/miniconda3/envs/ds/bin/python scripts/train_and_predict.py \
        --npz data/processed/S2A_51MTN_20241027_0_L2A_features.npz \
        --indices-tif data/processed/S2A_51MTN_20241027_0_L2A_indices.tif \
        --desa-json data/processed/S2A_51MTN_20241027_0_L2A_desa_summary.json \
        --out-dir data/processed
"""
import argparse
import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import rasterio
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB


def main():
    parser = argparse.ArgumentParser(description="Pelatihan Model & Prediksi Kelapa Selayar")
    parser.add_argument("--npz", default="data/processed/S2A_51MTN_20241027_0_L2A_features.npz")
    parser.add_argument("--indices-tif", default="data/processed/S2A_51MTN_20241027_0_L2A_indices.tif")
    parser.add_argument("--desa-json", default="data/processed/S2A_51MTN_20241027_0_L2A_desa_summary.json")
    parser.add_argument("--out-dir", default="data/processed")
    parser.add_argument("--sample-size", type=int, default=50000, help="Jumlah sampel pelatihan")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    print(f"=== 1. Memuat Dataset Fitur Spektral: {args.npz} ===")
    npz_data = np.load(args.npz)
    X = npz_data["features"]
    feature_names = list(npz_data["feature_names"])
    y = npz_data["is_coconut_candidate"].astype(np.int32)
    x_utm = npz_data["x_utm"]
    y_utm = npz_data["y_utm"]
    desa_ids = npz_data["desa_id"]

    n_total = len(X)
    print(f"Total piksel teridentifikasi: {n_total:,} baris x {X.shape[1]} fitur")
    print(f"Rasio kelas target (kandidat kelapa): {y.mean() * 100:.1f}%\n")

    # 2. Stratified Sampling untuk efisiensi pelatihan
    # ponytail: 50k stratified sample prevents memory thrash and trains in <2s. Upgrade to full dataset when distributed cluster used.
    sample_sz = min(args.sample_size, n_total)
    rng = np.random.RandomState(42)
    sample_idx = rng.choice(n_total, size=sample_sz, replace=False)

    X_sample, y_sample = X[sample_idx], y[sample_idx]
    X_train, X_test, y_train, y_test = train_test_split(
        X_sample, y_sample, test_size=0.25, random_state=42, stratify=y_sample
    )

    # 3. Model Benchmark
    models = {
        "LightGBM": lgb.LGBMClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, verbose=-1, n_jobs=-1),
        "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1),
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        "GaussianNB": GaussianNB(),
    }

    print("=== 2. Pelatihan & Evaluasi Komparatif Model ===")
    print(f"{'Model':18s} | {'Akurasi':8s} | {'Presisi':8s} | {'Recall':8s} | {'F1-Score':8s} | {'ROC-AUC':8s} | {'Latih (s)':9s}")
    print("-" * 88)

    benchmark_records = {}
    best_model_name = None
    best_f1 = -1.0

    for name, clf in models.items():
        t0 = time.time()
        clf.fit(X_train, y_train)
        t_train = time.time() - t0

        t0 = time.time()
        y_pred = clf.predict(X_test)
        t_infer = time.time() - t0

        y_prob = clf.predict_proba(X_test)[:, 1] if hasattr(clf, "predict_proba") else y_pred.astype(float)

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        auc = float(roc_auc_score(y_test, y_prob))

        benchmark_records[name] = {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(auc, 4),
            "train_time_s": round(t_train, 3),
            "infer_time_ms": round(t_infer * 1000, 2),
        }

        print(f"{name:18s} | {acc:8.4f} | {prec:8.4f} | {rec:8.4f} | {f1:8.4f} | {auc:8.4f} | {t_train:8.2f}s")

        if f1 > best_f1:
            best_f1 = f1
            best_model_name = name

    print(f"\nModel terbaik: {best_model_name} (F1 = {best_f1:.4f})")

    # Feature Importance (LightGBM & Random Forest)
    best_clf = models[best_model_name]
    feature_importances = {}
    if hasattr(best_clf, "feature_importances_"):
        imps = best_clf.feature_importances_
        sorted_idx = np.argsort(imps)[::-1]
        print(f"\nFitur Paling Berpengaruh ({best_model_name}):")
        for i in sorted_idx[:6]:
            fn = feature_names[i]
            val = float(imps[i])
            feature_importances[fn] = val
            print(f"  - {fn:10s}: {val:.2f}")

    benchmark_output = {
        "benchmark": benchmark_records,
        "best_model": best_model_name,
        "best_f1": round(best_f1, 4),
        "top_features": feature_importances,
    }
    with open(out_dir / "model_benchmark.json", "w") as f:
        json.dump(benchmark_output, f, indent=2)

    # 4. Prediksi Skala Penuh (2.7 Juta Piksel)
    print(f"\n=== 3. Inferensi Skala Penuh Menggunakan {best_model_name} ({n_total:,} piksel) ===")
    t0 = time.time()
    full_probs = best_clf.predict_proba(X)[:, 1].astype(np.float32)
    full_preds = (full_probs >= 0.50).astype(np.uint8)
    print(f"Inferensi selesai dalam {time.time() - t0:.2f} detik")

    total_pred_coco = int(full_preds.sum())
    print(f"Total Piksel Kelapa Terprediksi: {total_pred_coco:,} ({total_pred_coco * 0.01:,.1f} ha)")

    # 5. Rekapitulasi Prediksi per Desa
    print("\n=== 4. Menyusun Rekapitulasi Prediksi per Desa ===")
    with open(args.desa_json) as f:
        desa_summary_in = json.load(f)

    # Inisialisasi lookup id -> key
    id_to_key = {}
    for d_idx, (k, v) in enumerate(desa_summary_in.items(), start=1):
        id_to_key[d_idx] = k

    desa_pred_summary = {}
    for d_id, k in id_to_key.items():
        mask_d = desa_ids == d_id
        count_d = int(mask_d.sum())
        if count_d == 0:
            continue
        orig = desa_summary_in[k]
        pred_coco_d = int(full_preds[mask_d].sum())
        prob_mean_d = float(np.mean(full_probs[mask_d]))

        desa_pred_summary[k] = {
            "nmkec": orig["nmkec"],
            "nmdesa": orig["nmdesa"],
            "kddesa": orig["kddesa"],
            "total_land_ha": orig["total_land_ha"],
            "predicted_coconut_ha": round(pred_coco_d * 0.01, 1),
            "predicted_coconut_pct": round(pred_coco_d / max(count_d, 1) * 100, 1),
            "mean_confidence": round(prob_mean_d, 3),
            "model_used": best_model_name,
        }

    pred_json_path = out_dir / "desa_coconut_predictions.json"
    with open(pred_json_path, "w") as f:
        json.dump(desa_pred_summary, f, indent=2)
    print(f"Disimpan ringkasan prediksi per desa: {pred_json_path}")

    # 6. Tulis GeoTIFF Prediksi Spasial
    print("\n=== 5. Menulis GeoTIFF Spasial Prediksi Kelapa ===")
    with rasterio.open(args.indices_tif) as src:
        prof = src.profile.copy()
        inv_trans = ~src.transform

    prof.update(
        count=2,
        dtype="uint8",
        nodata=255,
        compress="deflate",
        tiled=True,
        blockxsize=256,
        blockysize=256,
    )

    # Koordinat ke grid raster
    cols, rows = inv_trans * (x_utm, y_utm)
    c_int = np.clip(np.round(cols).astype(np.int32), 0, prof["width"] - 1)
    r_int = np.clip(np.round(rows).astype(np.int32), 0, prof["height"] - 1)

    prob_band = np.full((prof["height"], prof["width"]), 255, dtype=np.uint8)
    class_band = np.full((prof["height"], prof["width"]), 255, dtype=np.uint8)

    # Probabilitas dikonversi ke skala 0 - 100
    prob_band[r_int, c_int] = np.clip(np.round(full_probs * 100), 0, 100).astype(np.uint8)
    class_band[r_int, c_int] = full_preds

    pred_tif_path = out_dir / "S2A_51MTN_coconut_prediction.tif"
    with rasterio.open(pred_tif_path, "w", **prof) as dst:
        dst.set_band_description(1, "Coconut_Probability_Pct")
        dst.set_band_description(2, "Coconut_Class_Binary")
        dst.write(prob_band, 1)
        dst.write(class_band, 2)

    print(f"Disimpan GeoTIFF Prediksi: {pred_tif_path} ({pred_tif_path.stat().st_size / (1024*1024):.1f} MB)")
    print(f"\nSelesai dalam {time.time() - t_start:.1f} detik!")


if __name__ == "__main__":
    main()
