"""
Versi generic training direct model untuk horizon berapa pun (parameterized),
objective L2. Metodologi identik di semua horizon -> tren lintas horizon
apple-to-apple (menyelesaikan confound recursive-vs-direct dari eksperimen awal).

Hasil tiap run diakumulasi ke models/ringkasan_horizon.csv.
Model disimpan sebagai models/model_direct_h{H}.txt (tidak menimpa model_h1.txt
yang dipakai eksperimen recursive).

Pemakaian: python3 scripts/train_model_horizon.py <horizon_dalam_hari>
"""

import sys
from pathlib import Path
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

HORIZON = int(sys.argv[1]) if len(sys.argv) > 1 else 7

df = pd.read_csv(DATA_PROCESSED / f"dataset_fitur_h{HORIZON}.csv", parse_dates=["tanggal", "tanggal_target"])
df["pasar"] = df["pasar"].astype("category")
df["komoditas"] = df["komoditas"].astype("category")
df["delta_hN"] = df["harga_target"] - df["harga"]

feature_cols = [
    "pasar", "komoditas",
    "harga_lag1", "harga_lag7", "harga_lag14",
    "harga_rolling7_mean", "harga_rolling7_std", "harga_rolling14_mean",
    "curah_hujan_mm", "suhu_avg", "suhu_max", "suhu_min",
    "curah_hujan_7hr", "curah_hujan_14hr",
    "kurs_usd_idr", "kurs_lag7",
    "hari_dalam_minggu_target", "bulan_target", "is_weekend_target", "hari_ke_lebaran_target",
]

tanggal_cutoff = df["tanggal_target"].max() - pd.Timedelta(days=60)
train_df = df[df["tanggal_target"] <= tanggal_cutoff]
test_df = df[df["tanggal_target"] > tanggal_cutoff]

X_train, y_train = train_df[feature_cols], train_df["delta_hN"]
X_test = test_df[feature_cols]

model = lgb.LGBMRegressor(
    objective="regression",
    n_estimators=500,
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=50,
    random_state=42,
)
model.fit(X_train, y_train, categorical_feature=["pasar", "komoditas"])

delta_pred = model.predict(X_test)
harga_pred = test_df["harga"] + delta_pred
y_true = test_df["harga_target"]
baseline_pred = test_df["baseline_hN"]

mae_model = mean_absolute_error(y_true, harga_pred)
mape_model = mean_absolute_percentage_error(y_true, harga_pred) * 100
mae_baseline = mean_absolute_error(y_true, baseline_pred)
mape_baseline = mean_absolute_percentage_error(y_true, baseline_pred) * 100
selisih_pct = (mae_model / mae_baseline - 1) * 100

print(f"=== H+{HORIZON} (train {len(train_df)} | test {len(test_df)}) ===")
print(f"Model    -> MAE Rp {mae_model:,.0f} | MAPE {mape_model:.2f}%")
print(f"Baseline -> MAE Rp {mae_baseline:,.0f} | MAPE {mape_baseline:.2f}%")
status = "model kalah" if selisih_pct > 0 else "model menang"
print(f"Selisih  : {selisih_pct:+.1f}% ({status})")

top5 = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False).head(5)
print("Top-5 importance:", ", ".join(f"{k}={v}" for k, v in top5.items()))

MODELS_DIR.mkdir(parents=True, exist_ok=True)
hasil = pd.DataFrame([{
    "horizon": HORIZON, "mae_model": round(mae_model), "mape_model": round(mape_model, 2),
    "mae_baseline": round(mae_baseline), "mape_baseline": round(mape_baseline, 2),
    "selisih_pct": round(selisih_pct, 1),
}])
ringkasan_path = MODELS_DIR / "ringkasan_horizon.csv"
if ringkasan_path.exists():
    existing = pd.read_csv(ringkasan_path)
    existing = existing[existing["horizon"] != HORIZON]
    hasil = pd.concat([existing, hasil], ignore_index=True)
hasil = hasil.sort_values("horizon")
hasil.to_csv(ringkasan_path, index=False)
print(f"\n=== Ringkasan kumulatif (models/ringkasan_horizon.csv) ===")
print(hasil.to_string(index=False))

model.booster_.save_model(str(MODELS_DIR / f"model_direct_h{HORIZON}.txt"))
