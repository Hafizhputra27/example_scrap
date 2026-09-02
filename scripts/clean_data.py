from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

df = pd.read_csv(ROOT / "data/raw/harga_sibapokting.csv")

sayuran_inti = [
    "BAWANG DAUN", "BAWANG MERAH", "BAWANG PUTIH BIASA",
    "CABE MERAH TANJUNG", "CABE MERAH KERITING", "CABE HIJAU BIASA",
    "CABE RAWIT HIJAU", "CABE RAWIT MERAH", "JAGUNG MANIS",
    "SAYURAN BUNCIS", "SAYURAN TOMAT", "SAYURAN KOL/KUBIS",
    "KENTANG DIENG", "SAYURAN WORTEL", "TOMAT HIJAU",
]

df_clean = df[df["komoditas"].isin(sayuran_inti)].copy()
df_clean["tanggal"] = pd.to_datetime(df_clean["tanggal"])
df_clean["harga"] = pd.to_numeric(df_clean["harga"], errors="coerce")

# Buang harga tidak masuk akal -- typo entri di situs sumber (mis. cabai Rp 50.000.000,
# kentang Rp 450.009, atau "45.000" keparse jadi Rp 45). Batas: 0,25x-4x median komoditas
# itu sendiri; cukup longgar untuk lonjakan cabai yang nyata (median 50rb -> s/d 200rb),
# cukup ketat untuk menangkap typo. Baris di luar batas -> harga jadi NaN (bukan di-drop),
# supaya grid harian tetap utuh untuk perhitungan lag/rolling di feature_engineering.
# ponytail: median-ratio band, ganti ke filter per-(pasar,komoditas) kalau ada pasar yang
# level harganya konsisten beda jauh dari pasar lain.
median_kom = df_clean.groupby("komoditas")["harga"].transform("median")
tidak_masuk_akal = ~df_clean["harga"].between(median_kom * 0.25, median_kom * 4) & df_clean["harga"].notna()
print(f"Harga tidak masuk akal di-NaN-kan: {tidak_masuk_akal.sum()} baris")
df_clean.loc[tidak_masuk_akal, "harga"] = pd.NA
df_clean["harga"] = pd.to_numeric(df_clean["harga"], errors="coerce")

df_clean = df_clean.sort_values(["tanggal", "pasar", "komoditas"]).reset_index(drop=True)

harga_valid = df_clean["harga"].dropna()
assert harga_valid.between(500, 500_000).all(), (
    f"Masih ada harga di luar 500-500.000: min={harga_valid.min()}, max={harga_valid.max()}"
)

df_clean.to_csv(ROOT / "data/processed/harga_sayur_bersih.csv", index=False)
print("Selesai. Total baris:", len(df_clean), "| harga terisi:", df_clean["harga"].notna().sum())