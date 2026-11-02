#!/usr/bin/env python3
"""Pelatihan Model Segmentasi Tutupan Lahan Multiclass Berimbang (Balanced Classes)
dengan Hyperparameter Tuning untuk Sentinel-2 Kepulauan Selayar.

Kelas:
    0: Kelapa (Pohon Kelapa / Cocos nucifera)
    1: Hutan (Hutan Tropis / Mangrove)
    2: Bangunan (Permukiman / Infrastruktur)
    3: Air (Badan Air / Tambak)
    4: Terbuka (Lahan Terbuka / Pasir / Batuan)

Usage:
    /Users/ridsonap/miniconda3/envs/ds/bin/python scripts/train_multiclass_segmentation.py
"""
import json
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score
from sklearn.model_selection import GridSearchCV, train_test_split


def build_balanced_dataset(npz_path, samples_per_class=8000, seed=42):
    print(f"Memuat dataset fitur: {npz_path}...")
    data = np.load(npz_path)
    X_all = data["features"]
    fn = list(data["feature_names"])

    ndvi = X_all[:, fn.index("NDVI")]
    ndre1 = X_all[:, fn.index("NDRE1")]
    ndwi = X_all[:, fn.index("NDWI")]
    bsi = X_all[:, fn.index("BSI")]
    b02 = X_all[:, fn.index("B02")]
    b04 = X_all[:, fn.index("B04")]
    b08 = X_all[:, fn.index("B08")]
    b11 = X_all[:, fn.index("B11")]
    b12 = X_all[:, fn.index("B12")]

    # Definisi spektral target berdasarkan data lapangan & citra resolusi tinggi
    # 0: Kelapa (NDVI tinggi sedang, NDRE khas, SWIR rendah-sedang, BSI negatif)
    mask_kelapa = (
        (ndvi >= 0.48) & (ndvi <= 0.82) &
        (ndre1 >= 0.24) & (ndre1 <= 0.58) &
        (b11 <= 0.22) & (bsi < -0.12) & (b04 < 0.07)
    )
    # 1: Hutan / Mangrove (Kanopi sangat rapat, NDVI & NDRE sangat tinggi, red sangat rendah)
    mask_hutan = (ndvi >= 0.78) & (ndre1 >= 0.48) & (b04 <= 0.045) & (bsi <= -0.25)
    # 2: Bangunan / Permukiman (BSI tinggi, NDVI rendah, refleksi merah & SWIR tinggi)
    mask_bangunan = (bsi >= -0.02) & (ndvi < 0.32) & (b04 >= 0.08)
    # 3: Badan Air (NDWI positif, NIR sangat rendah)
    mask_air = (ndwi >= 0.08) & (b08 <= 0.10)
    # 4: Lahan Terbuka / Pasir Pantai (BSI tinggi, NDVI rendah-sedang)
    mask_terbuka = (bsi >= -0.06) & (ndvi >= 0.12) & (ndvi < 0.38) & (b04 >= 0.06) & (~mask_bangunan)

    rng = np.random.RandomState(seed)
    masks = [mask_kelapa, mask_hutan, mask_bangunan, mask_air, mask_terbuka]
    class_names = ["Kelapa", "Hutan", "Bangunan", "Air", "Terbuka"]

    indices_list = []
    labels_list = []

    print("\n--- Distribusi Kandidat Sampel Sebelum Penyeimbangan ---")
    for c_id, (m, c_name) in enumerate(zip(masks, class_names)):
        pool_idx = np.where(m)[0]
        n_avail = len(pool_idx)
        print(f"  Kelas {c_id} ({c_name:10s}): {n_avail:8,d} piksel tersedia")
        n_draw = min(samples_per_class, n_avail)
        chosen = rng.choice(pool_idx, size=n_draw, replace=False)
        indices_list.append(chosen)
        labels_list.append(np.full(n_draw, c_id, dtype=int))

    sample_indices = np.concatenate(indices_list)
    y = np.concatenate(labels_list)
    X = X_all[sample_indices]

    print(f"\n--- Dataset Seimbang Siap (Total: {len(y):,d} sampel) ---")
    for c_id, c_name in enumerate(class_names):
        cnt = (y == c_id).sum()
        print(f"  Kelas {c_id} ({c_name:10s}): {cnt:6,d} sampel ({cnt/len(y)*100:5.1f}%)")

    return X, y, fn, class_names


def main():
    t_start = time.time()
    npz_path = "data/processed/S2A_51MTN_20241027_0_L2A_features.npz"
    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Dataset berimbang
    X, y, feature_names, class_names = build_balanced_dataset(npz_path, samples_per_class=6000)

    # 2. Train-test split (75% train, 25% test berstrata)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # 3. Hyperparameter Tuning dengan GridSearchCV
    print("\n=== Melakukan Hyperparameter Tuning Random Forest (3-Fold CV) ===")
    param_grid = {
        "n_estimators": [60, 100],
        "max_depth": [8, 12, 16],
        "min_samples_split": [2, 5],
    }
    base_rf = RandomForestClassifier(random_state=42, class_weight="balanced")
    grid_search = GridSearchCV(
        base_rf,
        param_grid,
        cv=3,
        scoring="f1_weighted",
        n_jobs=4,
        verbose=1,
    )

    t0 = time.time()
    grid_search.fit(X_train, y_train)
    t_tune = time.time() - t0
    print(f"Tuning selesai dalam {t_tune:.2f} detik.")
    print(f"Parameter Terbaik: {grid_search.best_params_}")
    print(f"Skor F1-Weighted CV Terbaik: {grid_search.best_score_:.4f}")

    best_model = grid_search.best_estimator_

    # 4. Evaluasi Independen pada Test Set
    t0 = time.time()
    y_pred = best_model.predict(X_test)
    y_prob = best_model.predict_proba(X_test)
    t_infer = (time.time() - t0) / len(X_test) * 1000

    acc = accuracy_score(y_test, y_pred)
    f1_w = f1_score(y_test, y_pred, average="weighted")
    cm = confusion_matrix(y_test, y_pred)
    rep = classification_report(y_test, y_pred, target_names=class_names, output_dict=True)

    print("\n=== Evaluasi Model pada Data Uji Independen (Test Set) ===")
    print(f"Akurasi Keseluruhan : {acc * 100:.2f}%")
    print(f"F1-Score (Weighted) : {f1_w * 100:.2f}%")
    print(f"Kecepatan Inferensi : {t_infer:.4f} ms per piksel\n")
    print(classification_report(y_test, y_pred, target_names=class_names, digits=4))

    print("Confusion Matrix:")
    print("Pred ->   " + "  ".join(f"{c[:6]:>7s}" for c in class_names))
    for i, row in enumerate(cm):
        print(f"Aktual {class_names[i][:6]:>6s}: " + "  ".join(f"{v:7d}" for v in row))

    # 5. Feature Importance
    importances = best_model.feature_importances_
    sorted_feat = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
    print("\nBobot Fitur Spektral Paling Berpengaruh:")
    for fn_name, imp in sorted_feat[:8]:
        print(f"  {fn_name:10s}: {imp * 100:5.2f}%")

    # 6. Simpan Model & Metadata Evaluasi
    model_path = out_dir / "multiclass_segmentation_rf.joblib"
    joblib.dump(best_model, model_path)
    print(f"\nModel tersimpan di: {model_path}")

    meta = {
        "model": "RandomForestClassifier",
        "best_params": grid_search.best_params_,
        "cv_f1_score": round(float(grid_search.best_score_), 4),
        "test_accuracy": round(float(acc), 4),
        "test_f1_weighted": round(float(f1_w), 4),
        "class_performance": {
            c_name: {
                "precision": round(float(rep[c_name]["precision"]), 4),
                "recall": round(float(rep[c_name]["recall"]), 4),
                "f1_score": round(float(rep[c_name]["f1-score"]), 4),
                "support": int(rep[c_name]["support"]),
            }
            for c_name in class_names
        },
        "confusion_matrix": cm.tolist(),
        "feature_importances": {fn_name: round(float(imp), 4) for fn_name, imp in sorted_feat},
        "training_time_s": round(t_tune, 2),
    }

    with open(out_dir / "multiclass_evaluation.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Metadata evaluasi tersimpan di: {out_dir / 'multiclass_evaluation.json'}")
    print(f"Selesai dalam {time.time() - t_start:.2f} detik.")


if __name__ == "__main__":
    main()
