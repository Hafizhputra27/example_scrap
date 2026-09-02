"""
Versi generic dari pembangunan dataset direct model untuk horizon berapa pun
(parameterized), biar bisa dibandingkan apple-to-apple lintas horizon dengan
metodologi yang sama persis (bukan campuran recursive + direct).

Anchor date = "hari ini", target = harga H hari kemudian. Fitur cuaca/kurs/lag
dari baris anchor tetap valid TANPA forecast (itu nilai aktual di tanggal anchor).
Fitur kalender dihitung ulang untuk tanggal_target (deterministik, tidak butuh
forecast).

Pemakaian: python3 scripts/build_dataset_horizon.py <horizon_dalam_hari>
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"

HORIZON = int(sys.argv[1]) if len(sys.argv) > 1 else 7

df = pd.read_csv(DATA_PROCESSED / "dataset_fitur.csv", parse_dates=["tanggal"])
df = df.sort_values(["pasar", "komoditas", "tanggal"]).reset_index(drop=True)

df["harga_target"] = df.groupby(["pasar", "komoditas"], observed=True)["harga"].shift(-HORIZON)
df["tanggal_target"] = df["tanggal"] + pd.Timedelta(days=HORIZON)

lebaran_dates = pd.to_datetime(["2025-03-31", "2026-03-21"])

def hari_ke_lebaran_terdekat(tanggal_series):
    tanggal_arr = tanggal_series.values.astype("datetime64[D]")
    lebaran_arr = lebaran_dates.values.astype("datetime64[D]")
    diffs = (lebaran_arr[None, :] - tanggal_arr[:, None]).astype("timedelta64[D]").astype(int)
    idx_terdekat = np.abs(diffs).argmin(axis=1)
    return diffs[np.arange(len(diffs)), idx_terdekat]

df["hari_dalam_minggu_target"] = df["tanggal_target"].dt.dayofweek
df["bulan_target"] = df["tanggal_target"].dt.month
df["is_weekend_target"] = df["hari_dalam_minggu_target"].isin([5, 6]).astype(int)
df["hari_ke_lebaran_target"] = hari_ke_lebaran_terdekat(df["tanggal_target"])

df["baseline_hN"] = df["harga"]  # persistence: harga H hari ke depan = harga hari ini

# ponytail: shift(-H) = H baris ke depan, bukan H hari kalender. Grid harian
# 99,9% rapat (gap=1 utk 98550/98685 baris) jadi ~ekuivalen; tanggal_target tetap
# dihitung kalender-akurat untuk fitur kalender.
df = df.dropna(subset=["harga", "harga_target"]).reset_index(drop=True)

output_path = DATA_PROCESSED / f"dataset_fitur_h{HORIZON}.csv"
df.to_csv(output_path, index=False)
print(f"Horizon H+{HORIZON}: {len(df)} baris. Disimpan ke {output_path}")
