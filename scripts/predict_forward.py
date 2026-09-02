"""
Prediksi harga ke depan (H+1, H+3, H+7) dari data historis terakhir.

Untuk tiap kombinasi (pasar, komoditas): ambil baris terakhir yang harga & fitur
lag-nya lengkap sebagai ANCHOR ("hari ini"), hitung fitur kalender untuk tanggal
target, jalankan model_direct_h{1,3,7}.txt -> delta -> harga_prediksi = harga
anchor + delta. Baseline = harga anchor (persistence).

CATATAN JUJUR yang harus ditampilkan di dashboard:
- Prediksi ini "dari tanggal data terakhir", bukan dari hari ini (SIBAPOKTING
  tanpa API). Kalau data terakhir 22 Agu 2026, H+7 = 29 Agu 2026.
- Model secara historis MAE-nya DI ATAS baseline persistence di semua horizon
  (lihat models/ringkasan_horizon.csv). Prediksi model TIDAK boleh ditampilkan
  sendirian tanpa baseline + konteks ini.

Output: models/prediksi_forward.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "processed"
MODELS = BASE / "models"

HORIZONS = [1, 3, 7]
LEBARAN = pd.to_datetime(["2025-03-31", "2026-03-21"])

FEATURE_COLS = [
    "pasar", "komoditas",
    "harga_lag1", "harga_lag7", "harga_lag14",
    "harga_rolling7_mean", "harga_rolling7_std", "harga_rolling14_mean",
    "curah_hujan_mm", "suhu_avg", "suhu_max", "suhu_min",
    "curah_hujan_7hr", "curah_hujan_14hr",
    "kurs_usd_idr", "kurs_lag7",
    "hari_dalam_minggu_target", "bulan_target", "is_weekend_target", "hari_ke_lebaran_target",
]
ANCHOR_FEATURES = [c for c in FEATURE_COLS if not c.endswith("_target") and c not in ("pasar", "komoditas")]


def hari_ke_lebaran(tanggal):
    return min(((tanggal - l).days for l in LEBARAN), key=abs)


df = pd.read_csv(DATA / "dataset_fitur.csv", parse_dates=["tanggal"])
df = df.sort_values(["pasar", "komoditas", "tanggal"])

# anchor = baris terakhir per (pasar, komoditas) dengan harga & semua fitur anchor lengkap
lengkap = df.dropna(subset=["harga"] + ANCHOR_FEATURES)
anchor = lengkap.groupby(["pasar", "komoditas"], as_index=False).last()

models = {h: lgb.Booster(model_file=str(MODELS / f"model_direct_h{h}.txt")) for h in HORIZONS}
ringkasan = pd.read_csv(MODELS / "ringkasan_horizon.csv").set_index("horizon")

anchor["pasar"] = anchor["pasar"].astype("category")
anchor["komoditas"] = anchor["komoditas"].astype("category")

hasil = anchor[["pasar", "komoditas", "tanggal", "harga"]].rename(
    columns={"tanggal": "tanggal_anchor", "harga": "harga_terakhir"}
).copy()

for h in HORIZONS:
    tgl_target = anchor["tanggal"] + pd.Timedelta(days=h)
    X = anchor[ANCHOR_FEATURES].copy()
    X.insert(0, "komoditas", anchor["komoditas"].values)
    X.insert(0, "pasar", anchor["pasar"].values)
    X["hari_dalam_minggu_target"] = tgl_target.dt.dayofweek.values
    X["bulan_target"] = tgl_target.dt.month.values
    X["is_weekend_target"] = tgl_target.dt.dayofweek.isin([5, 6]).astype(int).values
    X["hari_ke_lebaran_target"] = [hari_ke_lebaran(t) for t in tgl_target]
    X = X[FEATURE_COLS]

    delta = models[h].predict(X)
    hasil[f"tanggal_target_h{h}"] = tgl_target.dt.date.values
    hasil[f"pred_model_h{h}"] = (anchor["harga"].values + delta).round().astype(int)
    hasil[f"pred_baseline_h{h}"] = anchor["harga"].values.round().astype(int)  # persistence
    hasil[f"mae_model_hist_h{h}"] = round(ringkasan.loc[h, "mae_model"])
    hasil[f"mae_baseline_hist_h{h}"] = round(ringkasan.loc[h, "mae_baseline"])
    hasil[f"model_lebih_buruk_pct_h{h}"] = round(ringkasan.loc[h, "selisih_pct"], 1)

hasil["tanggal_anchor"] = hasil["tanggal_anchor"].dt.date
hasil = hasil.sort_values(["komoditas", "pasar"]).reset_index(drop=True)

out = MODELS / "prediksi_forward.csv"
hasil.to_csv(out, index=False)
print(f"Prediksi forward untuk {len(hasil)} kombinasi (pasar x komoditas). Disimpan ke {out}")
print(f"Tanggal anchor terbaru: {hasil['tanggal_anchor'].max()} | terlama: {hasil['tanggal_anchor'].min()}")
basi = hasil[hasil["tanggal_anchor"] < df["tanggal"].max().date() - pd.Timedelta(days=14)]
if len(basi):
    print(f"PERINGATAN: {len(basi)} kombinasi anchor-nya > 14 hari lebih tua dari data terbaru "
          f"(pasar jarang lapor): {sorted(set(basi['komoditas'].astype(str)))}")
print()
print(hasil.head(6).to_string())
