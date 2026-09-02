"""
Training model LightGBM pertama untuk prediksi harga (horizon H+1),
dibandingkan dengan baseline naif (harga hari ini = harga kemarin).

Target model = SELISIH harga besok vs harga hari ini (harga - harga_lag1),
bukan level harga absolut. Alasannya: harga sayur sangat "lengket" hari ke
hari (baseline MAPE cuma ~2,6%), dan tree model tidak bisa mengekstrapolasi
level harga ke luar rentang training. Dengan target selisih, model cukup
belajar koreksi kecil di atas harga kemarin, dan prediksi akhir direkonstruksi
sebagai harga_lag1 + prediksi_selisih.

Kalau model ini tidak lebih baik dari baseline, berarti ada yang perlu
diperbaiki sebelum lanjut ke tahap berikutnya (H+2, H+3).
"""

from pathlib import Path
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
import lightgbm as lgb

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

df = pd.read_csv(DATA_PROCESSED / "dataset_fitur.csv", parse_dates=["tanggal"])
print("Shape awal:", df.shape)

# drop baris yang harga-nya (target) kosong -- tidak bisa dipakai untuk training/evaluasi
df = df.dropna(subset=["harga"]).reset_index(drop=True)
print("Shape setelah drop target kosong:", df.shape)

# butuh harga kemarin sebagai jangkar (baik untuk target selisih maupun baseline);
# baris tanpa harga_lag1 tidak bisa dipakai
df = df.dropna(subset=["harga_lag1"]).reset_index(drop=True)
print("Shape setelah drop tanpa harga_lag1:", df.shape)

# target = selisih harga besok vs harga hari ini
df["target_delta"] = df["harga"] - df["harga_lag1"]

# ubah pasar & komoditas jadi categorical, biar LightGBM bisa handle native
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
target_col = "target_delta"

# split berdasarkan waktu: 2 bulan terakhir jadi test set (BUKAN random split)
tanggal_cutoff = df["tanggal"].max() - pd.Timedelta(days=60)
train_df = df[df["tanggal"] <= tanggal_cutoff]
test_df = df[df["tanggal"] > tanggal_cutoff]

print(f"\nTrain: {len(train_df)} baris (sampai {tanggal_cutoff.date()})")
print(f"Test : {len(test_df)} baris (setelah {tanggal_cutoff.date()})")

X_train, y_train = train_df[feature_cols], train_df[target_col]
X_test, y_test = test_df[feature_cols], test_df[target_col]

# --- Model LightGBM ---
# Catatan: objective L1 sempat dicoba tapi kolaps -- target selisih mayoritas persis 0,
# L1 menemukan konstanta 0 sebagai MAE-optimal sehingga semua tree jadi nol dan model
# identik dengan baseline persistence (tautologi, bukan hasil). L2 dipakai supaya model
# menghasilkan prediksi non-trivial yang bisa diuji lawan baseline di tiap horizon.
# min_child_samples dinaikin biar tidak terlalu ngepas ke noise cuaca/kurs.
model = lgb.LGBMRegressor(
    n_estimators=500,
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=100,
    random_state=42,
)
model.fit(X_train, y_train, categorical_feature=["pasar", "komoditas"])

# model memprediksi SELISIH -> rekonstruksi ke level harga: harga_lag1 + selisih
pred_delta = model.predict(X_test)
harga_hat_model = test_df["harga_lag1"].to_numpy() + pred_delta

# --- Baseline naif: harga besok = harga hari ini (selisih = 0) ---
harga_hat_baseline = test_df["harga_lag1"].to_numpy()

# --- Evaluasi (di level harga, baris yang sama untuk model & baseline) ---
harga_aktual = test_df["harga"].to_numpy()

mae_model = mean_absolute_error(harga_aktual, harga_hat_model)
mape_model = mean_absolute_percentage_error(harga_aktual, harga_hat_model) * 100

mae_baseline = mean_absolute_error(harga_aktual, harga_hat_baseline)
mape_baseline = mean_absolute_percentage_error(harga_aktual, harga_hat_baseline) * 100

print("\n=== Hasil Evaluasi (test set, 2 bulan terakhir) ===")
print(f"Model LightGBM  -> MAE: Rp {mae_model:,.0f} | MAPE: {mape_model:.2f}%")
print(f"Baseline naif   -> MAE: Rp {mae_baseline:,.0f} | MAPE: {mape_baseline:.2f}%")

if mae_model < mae_baseline:
    improvement = (1 - mae_model / mae_baseline) * 100
    print(f"\n>> Model LEBIH BAIK dari baseline, error turun {improvement:.1f}%")
else:
    print("\n>> Model BELUM lebih baik dari baseline -- perlu tuning/perbaikan fitur")

# --- Feature importance ---
print("\n=== Feature importance ===")
importance_df = pd.DataFrame({
    "fitur": feature_cols,
    "importance": model.feature_importances_,
}).sort_values("importance", ascending=False)
print(importance_df.to_string(index=False))

MODELS_DIR.mkdir(parents=True, exist_ok=True)
model.booster_.save_model(str(MODELS_DIR / "model_h1.txt"))
print(f"\nModel disimpan ke {MODELS_DIR / 'model_h1.txt'}")