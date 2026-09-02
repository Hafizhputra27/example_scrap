"""
Feature engineering dari dataset_gabungan.csv.

Fitur yang dibuat:
1. Lag harga (harga kemarin, 7 hari lalu, 14 hari lalu) -- per kombinasi pasar+komoditas
2. Rolling statistics harga (rata-rata & std 7/14 hari) -- per kombinasi pasar+komoditas
3. Fitur kalender (hari dalam minggu, bulan, akhir pekan)
4. Curah hujan kumulatif (7/14 hari) -- per pasar, karena efek cuaca ke harga biasanya delay
5. Lag kurs (kurs 7 hari lalu) -- kurs sama untuk semua pasar/komoditas

PENTING: lag & rolling harus dihitung per kombinasi (pasar, komoditas) secara terpisah --
kalau tidak, harga cabai di Pasar A bisa "bocor" jadi lag buat harga cabai di Pasar B.
Makanya semua operasi ini pakai .groupby(["pasar", "komoditas"]) dulu.
"""

from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"

df = pd.read_csv(PROCESSED / "dataset_gabungan.csv", parse_dates=["tanggal"])
df = df.sort_values(["pasar", "komoditas", "tanggal"]).reset_index(drop=True)

print("Shape awal:", df.shape)

# --- 1. Lag harga (per pasar+komoditas) ---
g = df.groupby(["pasar", "komoditas"])["harga"]
df["harga_lag1"] = g.shift(1)
df["harga_lag7"] = g.shift(7)
df["harga_lag14"] = g.shift(14)

# --- 2. Rolling statistics harga (per pasar+komoditas) ---
# shift(1) dulu sebelum rolling, supaya hari ini TIDAK ikut menghitung rata-ratanya sendiri
# (kalau tidak di-shift, ini bocor informasi dari masa depan / data leakage)
g_shifted = df.groupby(["pasar", "komoditas"])["harga"].shift(1)
df["harga_rolling7_mean"] = g_shifted.groupby([df["pasar"], df["komoditas"]]).transform(
    lambda x: x.rolling(window=7, min_periods=1).mean()
)
df["harga_rolling7_std"] = g_shifted.groupby([df["pasar"], df["komoditas"]]).transform(
    lambda x: x.rolling(window=7, min_periods=1).std()
)
df["harga_rolling14_mean"] = g_shifted.groupby([df["pasar"], df["komoditas"]]).transform(
    lambda x: x.rolling(window=14, min_periods=1).mean()
)

# --- 3. Fitur kalender ---
df["hari_dalam_minggu"] = df["tanggal"].dt.dayofweek  # 0=Senin, 6=Minggu
df["bulan"] = df["tanggal"].dt.month
df["is_weekend"] = df["hari_dalam_minggu"].isin([5, 6]).astype(int)

# --- 4. Curah hujan kumulatif (per pasar, bukan per komoditas -- cuaca sama untuk semua sayur) ---
df["curah_hujan_7hr"] = df.groupby("pasar")["curah_hujan_mm"].transform(
    lambda x: x.rolling(window=7, min_periods=1).sum()
)
df["curah_hujan_14hr"] = df.groupby("pasar")["curah_hujan_mm"].transform(
    lambda x: x.rolling(window=14, min_periods=1).sum()
)

# --- 5. Lag kurs (kurs sama untuk semua baris di tanggal yang sama, jadi cukup di-shift per tanggal unik) ---
kurs_unik = df[["tanggal", "kurs_usd_idr"]].drop_duplicates().sort_values("tanggal")
kurs_unik["kurs_lag7"] = kurs_unik["kurs_usd_idr"].shift(7)
df = df.merge(kurs_unik[["tanggal", "kurs_lag7"]], on="tanggal", how="left")

print("Shape setelah tambah fitur:", df.shape)
print("\nKolom yang ada sekarang:")
print(df.columns.tolist())

print("\nCek berapa baris punya NaN di fitur lag14 (wajar tinggi karena 14 hari pertama tiap pasar+komoditas belum punya histori):")
print(df["harga_lag14"].isna().sum(), "dari", len(df))

output_path = PROCESSED / "dataset_fitur.csv"
df.to_csv(output_path, index=False)
print(f"\nDisimpan ke {output_path}")
print()
print(df[df["komoditas"] == "BAWANG MERAH"][df["pasar"] == "Pasar Margahayu"].head(20).to_string())