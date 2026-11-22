"""
Reframe H+1 dari regresi (prediksi angka harga) jadi klasifikasi (prediksi arah:
naik / turun / stabil). Hipotesis: meski magnitude harga ~random walk (sudah
dibuktikan di eksperimen sebelumnya), arah pergerakan mungkin lebih bisa
ditangkap -- dan ini yang sebetulnya dibutuhkan untuk rekomendasi ke petani
("jual sekarang atau tunggu"), bukan angka rupiah presisi.

Threshold: >+2% = naik, <-2% = turun, di antaranya = stabil.
Baseline pembanding: selalu tebak kelas mayoritas (biasanya "stabil").

HASIL (test = 60 hari terakhir, kelas: stabil 81,5% / naik 9,4% / turun 9,1%):
- Tanpa class_weight : akurasi 0,834 < baseline 0,838. recall naik/turun 0,08/0,05
  (model main aman ke "stabil"). precision naik 0,41 -- tapi cuma dari 107 call.
- class_weight="balanced" : akurasi 0,756. recall naik/turun naik ke 0,31/0,30,
  TAPI precision ambruk ke 0,23/0,21 (base rate ~9%), dan di antara call
  directional ~44-47% terbalik total (naik<->turun). Precision 0,41 tadi = artefak
  sampel kecil, bukan sinyal ketutup imbalance.
Kesimpulan: arah pergerakan harga juga ~random di H+1. Lihat memori proyek.
"""

from pathlib import Path
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

df = pd.read_csv(DATA_PROCESSED / "dataset_fitur.csv", parse_dates=["tanggal"])
df = df.dropna(subset=["harga", "harga_lag1"]).reset_index(drop=True)

df["pasar"] = df["pasar"].astype("category")
df["komoditas"] = df["komoditas"].astype("category")

# --- Target: arah pergerakan harga ---
df["delta_pct"] = (df["harga"] - df["harga_lag1"]) / df["harga_lag1"] * 100

def klasifikasi_arah(pct):
    if pct > 2:
        return "naik"
    elif pct < -2:
        return "turun"
    return "stabil"

df["arah"] = df["delta_pct"].apply(klasifikasi_arah)

print("Distribusi kelas (semua data):")
print(df["arah"].value_counts())
print(df["arah"].value_counts(normalize=True) * 100)

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
target_col = "arah"

# split waktu, sama seperti eksperimen sebelumnya
tanggal_cutoff = df["tanggal"].max() - pd.Timedelta(days=60)
train_df = df[df["tanggal"] <= tanggal_cutoff]
test_df = df[df["tanggal"] > tanggal_cutoff]

print(f"\nTrain: {len(train_df)} baris | Test: {len(test_df)} baris")

X_train, y_train = train_df[feature_cols], train_df[target_col]
X_test, y_test = test_df[feature_cols], test_df[target_col]

model = lgb.LGBMClassifier(
    n_estimators=500,
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=50,
    class_weight="balanced",
    random_state=42,
)
model.fit(X_train, y_train, categorical_feature=["pasar", "komoditas"])

pred = model.predict(X_test)

# --- Baseline: selalu tebak kelas mayoritas ---
kelas_mayoritas = y_train.mode()[0]
pred_baseline = [kelas_mayoritas] * len(y_test)

print(f"\nKelas mayoritas (baseline): {kelas_mayoritas}")
print(f"\n=== Akurasi ===")
print(f"Model      : {accuracy_score(y_test, pred):.4f}")
print(f"Baseline   : {accuracy_score(y_test, pred_baseline):.4f}")

print("\n=== Classification report (model) ===")
print(classification_report(y_test, pred))

print("\n=== Confusion matrix (model) ===")
print("Baris = aktual, Kolom = prediksi")
labels = ["naik", "stabil", "turun"]
cm = confusion_matrix(y_test, pred, labels=labels)
print(pd.DataFrame(cm, index=labels, columns=labels))

print("\n=== Feature importance ===")
importance_df = pd.DataFrame({
    "fitur": feature_cols,
    "importance": model.feature_importances_,
}).sort_values("importance", ascending=False)
print(importance_df.to_string(index=False))

MODELS_DIR.mkdir(parents=True, exist_ok=True)
model.booster_.save_model(str(MODELS_DIR / "model_klasifikasi_arah_h1.txt"))
print(f"\nModel disimpan ke {MODELS_DIR / 'model_klasifikasi_arah_h1.txt'}")
