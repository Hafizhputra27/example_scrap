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

# Jarak (hari) ke Lebaran terdekat: POSITIF = sebelum, NEGATIF = sesudah.
# Konvensi ini dipakai model tersimpan -- predict_forward.py dan
# build_dataset_horizon.py wajib sama. "bulan" tidak cukup karena Lebaran ikut
# kalender lunar (geser ~11 hari/tahun).
# ponytail: hardcode tanggal Idul Fitri versi pemerintah -- update daftar ini kalau
# rentang data diperluas. Sinyal musiman dari sini = temuan awal, bukan kesimpulan kuat.
_lebaran = pd.to_datetime(["2025-03-31", "2026-03-21", "2027-03-10"])


def _kalender_lebaran(t):
    """(jarak_terdekat_bertanda, hari_sejak_lebaran_di_cap_90, di_dalam_window_30)."""
    jarak = min(((l - t).days for l in _lebaran), key=abs)
    sejak = min((t - l).days for l in _lebaran if t >= l) if t >= _lebaran.min() else 90
    return jarak, min(sejak, 90), int(abs(jarak) <= 30)


_kal = df["tanggal"].apply(_kalender_lebaran)
df["hari_ke_lebaran"] = [k[0] for k in _kal]
# Dua fitur event-window menggantikan jarak bertanda sebagai fitur model: nilai
# bertanda lompat ~354 hari saat Lebaran terdekat berganti (argmin), dan itu
# bertindak sebagai indeks waktu, bukan sinyal. Kolom `hari_ke_lebaran` tetap
# ada untuk skrip riset/band.
df["hari_sejak_lebaran"] = [k[1] for k in _kal]
df["is_lebaran_window"] = [k[2] for k in _kal]

# --- 4. Curah hujan kumulatif (per pasar, bukan per komoditas -- cuaca sama untuk semua sayur) ---
df["curah_hujan_7hr"] = df.groupby("pasar")["curah_hujan_mm"].transform(
    lambda x: x.rolling(window=7, min_periods=1).sum()
)
df["curah_hujan_14hr"] = df.groupby("pasar")["curah_hujan_mm"].transform(
    lambda x: x.rolling(window=14, min_periods=1).sum()
)

# --- 5. Kurs: retur, bukan level ---
# Level kurs hampir monoton dalam waktu (dan di luar rentang training, tree tidak
# bisa mengekstrapolasi), jadi level & lag-nya bertindak sebagai indeks waktu.
# Yang dipakai model: retur 7/30 hari (stasioner). `kurs_lag7` tetap ada untuk
# skrip riset lama, tidak masuk fitur model.
kurs_unik = df[["tanggal", "kurs_usd_idr"]].drop_duplicates().sort_values("tanggal")
kurs_unik["kurs_lag7"] = kurs_unik["kurs_usd_idr"].shift(7)
kurs_unik["kurs_ret_7"] = kurs_unik["kurs_usd_idr"].pct_change(7)
kurs_unik["kurs_ret_30"] = kurs_unik["kurs_usd_idr"].pct_change(30)
df = df.merge(kurs_unik[["tanggal", "kurs_lag7", "kurs_ret_7", "kurs_ret_30"]],
              on="tanggal", how="left")

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