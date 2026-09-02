"""
Cek robustness: apakah pergeseran median CABE MERAH TANJUNG jelang Lebaran
muncul di KEDUA event Lebaran (2025 & 2026), atau cuma satu -- karena kalau
cuma satu, itu sample-of-2 yang rawan fluke, sama persis seperti kejadian
"importance #3 dari 2 titik" yang sudah pernah ketahuan overfitting sebelumnya.

Window disamakan dengan rekomendasi_band_h7.py: 21 hari SEBELUM s/d 7 hari
SESUDAH Lebaran (menangkap run-up harga, bukan aftermath).
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"

df = pd.read_csv(DATA_PROCESSED / "dataset_fitur_h7.csv", parse_dates=["tanggal", "tanggal_target"])
df["delta_pct_7hr"] = (df["harga_target"] - df["harga"]) / df["harga"] * 100

lebaran_2025 = pd.Timestamp("2025-03-31")
lebaran_2026 = pd.Timestamp("2026-03-21")

# selisih hari tanggal_target ke Lebaran: negatif = sebelum, positif = sesudah.
# window run-up: 21 hari sebelum (-21) s/d 7 hari sesudah (+7).
mask_2025 = (df["tanggal_target"] - lebaran_2025).dt.days.between(-21, 7)
mask_2026 = (df["tanggal_target"] - lebaran_2026).dt.days.between(-21, 7)

df["lebaran_event"] = "normal"
df.loc[mask_2025, "lebaran_event"] = "lebaran_2025"
df.loc[mask_2026, "lebaran_event"] = "lebaran_2026"

target_komoditas = ["CABE MERAH TANJUNG", "CABE MERAH KERITING", "SAYURAN TOMAT", "TOMAT HIJAU", "CABE HIJAU BIASA"]

for kom in target_komoditas:
    sub = df[df["komoditas"] == kom]
    print(f"\n=== {kom} ===")
    ringkasan = sub.groupby("lebaran_event")["delta_pct_7hr"].agg(
        n="count",
        median="median",
        p10=lambda x: x.quantile(0.10),
        p90=lambda x: x.quantile(0.90),
    )
    # urutkan: normal, lalu dua event
    ringkasan = ringkasan.reindex(["normal", "lebaran_2025", "lebaran_2026"])
    print(ringkasan.round(2).to_string())
