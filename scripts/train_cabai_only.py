"""
Uji ulang H+1 tapi HANYA untuk keluarga cabai (5 varian paling volatil dari 15
komoditas). Pertanyaan: masalah "tidak ada sinyal" itu karena horizon terlalu
pendek, atau karena pooling 15 komoditas terlalu beragam -- sinyal cabai (volatil,
ada pola musiman/lebaran) keencer sama kentang/kol yang mayoritas "stabil"?

Reuse pipeline & fitur yang sama, cuma filter subset. Dua eksperimen sekaligus:
1. Regresi delta harga (L2) vs baseline persistence -- metrik MAE
2. Klasifikasi arah (naik/turun/stabil, threshold +/-2%, class_weight balanced)
   vs baseline tebak kelas mayoritas

Catatan: "CABE MERAH TW" tidak ada di 15 komoditas inti (harga_sayur_bersih),
jadi cabai di sini = KERITING, TANJUNG, HIJAU BIASA, RAWIT HIJAU, RAWIT MERAH.
"""

from pathlib import Path
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import (
    mean_absolute_error, mean_absolute_percentage_error,
    classification_report, confusion_matrix, accuracy_score,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"

feature_cols = [
    "pasar", "komoditas",
    "harga_lag1", "harga_lag7", "harga_lag14",
    "harga_rolling7_mean", "harga_rolling7_std", "harga_rolling14_mean",
    "curah_hujan_mm", "suhu_avg", "suhu_max", "suhu_min",
    "curah_hujan_7hr", "curah_hujan_14hr",
    "kurs_usd_idr", "kurs_lag7",
    "hari_dalam_minggu", "bulan", "is_weekend",
    "hari_ke_lebaran",
]

df = pd.read_csv(DATA_PROCESSED / "dataset_fitur.csv", parse_dates=["tanggal"])
df = df[df["komoditas"].str.contains("CABE")].copy()
df = df.dropna(subset=["harga", "harga_lag1"]).reset_index(drop=True)
df["pasar"] = df["pasar"].astype("category")
df["komoditas"] = df["komoditas"].astype("category")

print("Komoditas:", sorted(df["komoditas"].unique().tolist()))
print("Total baris cabai (harga & lag1 ada):", len(df))

tanggal_cutoff = df["tanggal"].max() - pd.Timedelta(days=60)
train_df = df[df["tanggal"] <= tanggal_cutoff]
test_df = df[df["tanggal"] > tanggal_cutoff]
print(f"Train: {len(train_df)} | Test: {len(test_df)} (setelah {tanggal_cutoff.date()})")

# ================= 1. REGRESI DELTA =================
print("\n" + "=" * 55)
print("1. REGRESI: prediksi selisih harga (harga - harga_lag1)")
print("=" * 55)

y_train_delta = train_df["harga"] - train_df["harga_lag1"]
reg = lgb.LGBMRegressor(
    n_estimators=500, learning_rate=0.05, num_leaves=31,
    min_child_samples=100, random_state=42,
)
reg.fit(train_df[feature_cols], y_train_delta, categorical_feature=["pasar", "komoditas"])

harga_hat = test_df["harga_lag1"].to_numpy() + reg.predict(test_df[feature_cols])
harga_aktual = test_df["harga"].to_numpy()
base_hat = test_df["harga_lag1"].to_numpy()

mae_model = mean_absolute_error(harga_aktual, harga_hat)
mae_base = mean_absolute_error(harga_aktual, base_hat)
print(f"Model    -> MAE Rp {mae_model:,.0f} | MAPE {mean_absolute_percentage_error(harga_aktual, harga_hat)*100:.2f}%")
print(f"Baseline -> MAE Rp {mae_base:,.0f} | MAPE {mean_absolute_percentage_error(harga_aktual, base_hat)*100:.2f}%")
print(f">> Model {'MENANG' if mae_model < mae_base else 'KALAH'} "
      f"({(mae_model/mae_base - 1)*100:+.1f}% vs baseline)")

# ================= 2. KLASIFIKASI ARAH =================
print("\n" + "=" * 55)
print("2. KLASIFIKASI: arah (naik >+2% / turun <-2% / stabil)")
print("=" * 55)

def arah(pct):
    return "naik" if pct > 2 else "turun" if pct < -2 else "stabil"

df["arah"] = ((df["harga"] - df["harga_lag1"]) / df["harga_lag1"] * 100).apply(arah)
train_df = df[df["tanggal"] <= tanggal_cutoff]
test_df = df[df["tanggal"] > tanggal_cutoff]

print("Distribusi kelas (semua data cabai):")
print((df["arah"].value_counts(normalize=True) * 100).round(1).to_string())

clf = lgb.LGBMClassifier(
    n_estimators=500, learning_rate=0.05, num_leaves=31,
    min_child_samples=50, class_weight="balanced", random_state=42,
)
clf.fit(train_df[feature_cols], train_df["arah"], categorical_feature=["pasar", "komoditas"])
pred = clf.predict(test_df[feature_cols])

kelas_mayoritas = train_df["arah"].mode()[0]
base_pred = [kelas_mayoritas] * len(test_df)
print(f"\nAkurasi  model: {accuracy_score(test_df['arah'], pred):.4f} | "
      f"baseline ('{kelas_mayoritas}'): {accuracy_score(test_df['arah'], base_pred):.4f}")

print("\nClassification report (model):")
print(classification_report(test_df["arah"], pred))

labels = ["naik", "stabil", "turun"]
cm = confusion_matrix(test_df["arah"], pred, labels=labels)
print("Confusion matrix (baris=aktual, kolom=prediksi):")
print(pd.DataFrame(cm, index=labels, columns=labels))
