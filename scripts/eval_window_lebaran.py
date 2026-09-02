"""
Tes yang benar untuk fitur hari_ke_lebaran: split waktu supaya test set MENCAKUP
Lebaran 2026 (21 Mar 2026). Test = 2026-02-01 s/d 2026-05-01 (run-up + Lebaran +
aftermath). Train = semua sebelum 2026-02-01 -- masih memuat Lebaran 2025 buat
model belajar polanya.

Bandingkan 3 hal di window itu (regresi delta harga, metrik MAE):
- baseline persistence (harga_lag1)
- model DENGAN hari_ke_lebaran
- model TANPA hari_ke_lebaran

Kalau model+lebaran jelas mengalahkan model-lebaran DAN baseline di window ini
-> fitur Lebaran menangkap sinyal nyata (temuan awal, cuma 1 Lebaran di test).
Kalau tidak -> bukti keempat bahwa fitur yang ada tidak cukup.
"""

from pathlib import Path
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"

FEAT_BASE = [
    "pasar", "komoditas",
    "harga_lag1", "harga_lag7", "harga_lag14",
    "harga_rolling7_mean", "harga_rolling7_std", "harga_rolling14_mean",
    "curah_hujan_mm", "suhu_avg", "suhu_max", "suhu_min",
    "curah_hujan_7hr", "curah_hujan_14hr",
    "kurs_usd_idr", "kurs_lag7",
    "hari_dalam_minggu", "bulan", "is_weekend",
]

df = pd.read_csv(DATA_PROCESSED / "dataset_fitur.csv", parse_dates=["tanggal"])
df = df.dropna(subset=["harga", "harga_lag1"]).reset_index(drop=True)
df["pasar"] = df["pasar"].astype("category")
df["komoditas"] = df["komoditas"].astype("category")
df["target_delta"] = df["harga"] - df["harga_lag1"]

test_start = pd.Timestamp("2026-02-01")
test_end = pd.Timestamp("2026-05-01")
train_df = df[df["tanggal"] < test_start]


def eval_subset(nama, sub_train, sub_test):
    print(f"\n=== {nama} ===")
    print(f"train {len(sub_train)} | test {len(sub_test)} "
          f"({sub_test['tanggal'].min().date()}..{sub_test['tanggal'].max().date()})")
    y_true = sub_test["harga"].to_numpy()
    base_hat = sub_test["harga_lag1"].to_numpy()
    mae_base = mean_absolute_error(y_true, base_hat)
    print(f"  baseline persistence : MAE Rp {mae_base:,.0f}")

    for label, feats in [("TANPA lebaran", FEAT_BASE),
                         ("DENGAN lebaran", FEAT_BASE + ["hari_ke_lebaran"])]:
        m = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=31,
                              min_child_samples=100, random_state=42, verbose=-1)
        m.fit(sub_train[feats], sub_train["target_delta"],
              categorical_feature=["pasar", "komoditas"])
        hat = sub_test["harga_lag1"].to_numpy() + m.predict(sub_test[feats])
        mae = mean_absolute_error(y_true, hat)
        print(f"  model {label:14s} : MAE Rp {mae:,.0f}  ({(mae/mae_base-1)*100:+.1f}% vs baseline)")


test_all = df[(df["tanggal"] >= test_start) & (df["tanggal"] < test_end)]
eval_subset("SEMUA 15 KOMODITAS", train_df, test_all)

cabai_mask = df["komoditas"].astype(str).str.contains("CABE")
eval_subset("CABAI SAJA",
            train_df[train_df["komoditas"].astype(str).str.contains("CABE")],
            test_all[test_all["komoditas"].astype(str).str.contains("CABE")])

# fokus lagi: cuma H-14 s/d H+14 sekitar Lebaran
near = df[(df["hari_ke_lebaran"].between(-14, 14)) & (df["tanggal"] >= test_start)]
eval_subset("HANYA H-14..H+14 SEKITAR LEBARAN (semua komoditas)", train_df, near)
