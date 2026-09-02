"""
Tes terakhir: apakah model H+7 (direct, dengan fitur hari_ke_lebaran_target)
beneran unggul khusus di window Lebaran -- bukan cuma importance tinggi yang
belum tervalidasi seperti kejadian sebelumnya di H+1.

Window test: tanggal_target 2026-02-15 s/d 2026-04-15 (mencakup run-up +
Lebaran 21 Maret 2026 + aftermath). Train = semua data sebelum 2026-02-15
(masih memuat Lebaran 2025 buat model belajar pola).

Dua model dilatih dan dibandingkan DI WINDOW YANG SAMA:
1. Model lengkap (dengan hari_ke_lebaran_target)
2. Model tanpa fitur itu (semua fitur lain sama)
Kalau model (1) tidak jelas lebih baik dari (2) DAN dari baseline persistence
di window ini, itu bukti fitur Lebaran tidak actionable di horizon manapun.
"""

from pathlib import Path
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"

HORIZON = 7
df = pd.read_csv(DATA_PROCESSED / f"dataset_fitur_h{HORIZON}.csv", parse_dates=["tanggal", "tanggal_target"])
df["pasar"] = df["pasar"].astype("category")
df["komoditas"] = df["komoditas"].astype("category")
df["delta_hN"] = df["harga_target"] - df["harga"]

feature_cols_full = [
    "pasar", "komoditas",
    "harga_lag1", "harga_lag7", "harga_lag14",
    "harga_rolling7_mean", "harga_rolling7_std", "harga_rolling14_mean",
    "curah_hujan_mm", "suhu_avg", "suhu_max", "suhu_min",
    "curah_hujan_7hr", "curah_hujan_14hr",
    "kurs_usd_idr", "kurs_lag7",
    "hari_dalam_minggu_target", "bulan_target", "is_weekend_target", "hari_ke_lebaran_target",
]
feature_cols_no_lebaran = [c for c in feature_cols_full if c != "hari_ke_lebaran_target"]

# --- Split: train sebelum window Lebaran, test = window Lebaran 2026 ---
window_start = pd.Timestamp("2026-02-15")
window_end = pd.Timestamp("2026-04-15")

train_df = df[df["tanggal_target"] < window_start]
test_df = df[(df["tanggal_target"] >= window_start) & (df["tanggal_target"] <= window_end)]

print(f"Train: {len(train_df)} baris (sebelum {window_start.date()})")
print(f"Test (window Lebaran): {len(test_df)} baris ({window_start.date()} s/d {window_end.date()})")

def latih_dan_evaluasi(feature_cols, label):
    X_train, y_train = train_df[feature_cols], train_df["delta_hN"]
    X_test = test_df[feature_cols]

    model = lgb.LGBMRegressor(
        objective="regression", n_estimators=500, learning_rate=0.05,
        num_leaves=31, min_child_samples=50, random_state=42,
    )
    model.fit(X_train, y_train, categorical_feature=["pasar", "komoditas"])

    delta_pred = model.predict(X_test)
    harga_pred = test_df["harga"] + delta_pred
    mae = mean_absolute_error(test_df["harga_target"], harga_pred)
    mape = mean_absolute_percentage_error(test_df["harga_target"], harga_pred) * 100
    print(f"{label:35s} -> MAE Rp {mae:,.0f} | MAPE {mape:.2f}%")
    return mae

print("\n=== Hasil di window Lebaran 2026 ===")
mae_full = latih_dan_evaluasi(feature_cols_full, "Model + hari_ke_lebaran_target")
mae_no_lebaran = latih_dan_evaluasi(feature_cols_no_lebaran, "Model tanpa fitur Lebaran")

mae_baseline = mean_absolute_error(test_df["harga_target"], test_df["baseline_hN"])
mape_baseline = mean_absolute_percentage_error(test_df["harga_target"], test_df["baseline_hN"]) * 100
print(f"{'Baseline persistence (7 hari)':35s} -> MAE Rp {mae_baseline:,.0f} | MAPE {mape_baseline:.2f}%")

print("\n=== Verdict ===")
print(f"Fitur Lebaran membantu di window ini? {'YA' if mae_full < mae_no_lebaran else 'TIDAK'} "
      f"({'turun' if mae_full < mae_no_lebaran else 'naik'} {abs(mae_full - mae_no_lebaran):,.0f})")
print(f"Model (+lebaran) kalahkan baseline di window Lebaran? {'YA' if mae_full < mae_baseline else 'TIDAK'} "
      f"(model {mae_full:,.0f} vs baseline {mae_baseline:,.0f})")
