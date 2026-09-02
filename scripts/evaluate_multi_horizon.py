"""
Evaluasi model H+1 secara recursive untuk H+2 dan H+3.
Tidak training model baru -- pakai model_h1.txt yang sama, tapi untuk H+2/H+3
kolom harga_lag1 diganti dengan hasil prediksi horizon sebelumnya (bukan harga
aktual), karena di real inference nanti harga di hari mendatang memang belum
diketahui.

SIMPLIFIKASI yang perlu diketahui: harga_lag7, harga_lag14, dan rolling stats
tetap pakai nilai aktual/historis apa adanya (tidak dibuat recursive). Untuk
H+2 ini valid. Untuk H+3, rolling7_mean secara ketat "mengintip" 1-2 hari yang
seharusnya belum diketahui -- dampaknya kemungkinan kecil karena harga sangat
lengket, tapi ini limitasi yang perlu didokumentasikan di laporan, bukan
disembunyikan.

Baseline naif per horizon: persistence -- harga N hari sebelumnya, tanpa
perubahan (H+2 pakai harga 2 hari lalu, H+3 pakai harga 3 hari lalu).
"""

from pathlib import Path
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

df = pd.read_csv(DATA_PROCESSED / "dataset_fitur.csv", parse_dates=["tanggal"])
df = df.sort_values(["pasar", "komoditas", "tanggal"]).reset_index(drop=True)

df["pasar"] = df["pasar"].astype("category")
df["komoditas"] = df["komoditas"].astype("category")

feature_cols = [
    "pasar", "komoditas",
    "harga_lag1", "harga_lag7", "harga_lag14",
    "harga_rolling7_mean", "harga_rolling7_std", "harga_rolling14_mean",
    "curah_hujan_mm", "suhu_avg", "suhu_max", "suhu_min",
    "curah_hujan_7hr", "curah_hujan_14hr",
    "kurs_usd_idr", "kurs_lag7",
    "hari_dalam_minggu", "bulan", "is_weekend",
]

model = lgb.Booster(model_file=str(MODELS_DIR / "model_h1.txt"))

# --- H+1: fitur asli apa adanya (persis seperti waktu training) ---
delta_pred_h1 = model.predict(df[feature_cols])
df["pred_h1"] = df["harga_lag1"] + delta_pred_h1

# --- H+2: harga_lag1 diganti pred_h1 dari 1 hari sebelumnya (per pasar+komoditas) ---
df["lag1_untuk_h2"] = df.groupby(["pasar", "komoditas"], observed=True)["pred_h1"].shift(1)
X_h2 = df[feature_cols].copy()
X_h2["harga_lag1"] = df["lag1_untuk_h2"]
delta_pred_h2 = model.predict(X_h2)
df["pred_h2"] = df["lag1_untuk_h2"] + delta_pred_h2

# --- H+3: harga_lag1 diganti pred_h2 dari 1 hari sebelumnya ---
df["lag1_untuk_h3"] = df.groupby(["pasar", "komoditas"], observed=True)["pred_h2"].shift(1)
X_h3 = df[feature_cols].copy()
X_h3["harga_lag1"] = df["lag1_untuk_h3"]
delta_pred_h3 = model.predict(X_h3)
df["pred_h3"] = df["lag1_untuk_h3"] + delta_pred_h3

# --- Baseline naif per horizon: harga N hari sebelumnya (persistence) ---
df["baseline_h1"] = df["harga_lag1"]
df["baseline_h2"] = df.groupby(["pasar", "komoditas"], observed=True)["harga"].shift(2)
df["baseline_h3"] = df.groupby(["pasar", "komoditas"], observed=True)["harga"].shift(3)

# --- Evaluasi di test period yang sama seperti training H+1 (60 hari terakhir) ---
tanggal_cutoff = df["tanggal"].max() - pd.Timedelta(days=60)
test_df = df[df["tanggal"] > tanggal_cutoff].copy()
print(f"Test set: {len(test_df)} baris (setelah {tanggal_cutoff.date()})\n")

hasil = []
for horizon, pred_col, baseline_col in [
    ("H+1", "pred_h1", "baseline_h1"),
    ("H+2", "pred_h2", "baseline_h2"),
    ("H+3", "pred_h3", "baseline_h3"),
]:
    mask = test_df["harga"].notna() & test_df[pred_col].notna() & test_df[baseline_col].notna()
    y_true = test_df.loc[mask, "harga"]
    y_pred_model = test_df.loc[mask, pred_col]
    y_pred_baseline = test_df.loc[mask, baseline_col]

    hasil.append({
        "horizon": horizon,
        "n_baris": int(mask.sum()),
        "mae_model": mean_absolute_error(y_true, y_pred_model),
        "mape_model": mean_absolute_percentage_error(y_true, y_pred_model) * 100,
        "mae_baseline": mean_absolute_error(y_true, y_pred_baseline),
        "mape_baseline": mean_absolute_percentage_error(y_true, y_pred_baseline) * 100,
    })

hasil_df = pd.DataFrame(hasil)
hasil_df["model_menang"] = hasil_df["mae_model"] < hasil_df["mae_baseline"]
print(hasil_df.to_string(index=False))

hasil_df.to_csv(MODELS_DIR / "hasil_evaluasi_multi_horizon.csv", index=False)
print(f"\nDisimpan ke {MODELS_DIR / 'hasil_evaluasi_multi_horizon.csv'}")
