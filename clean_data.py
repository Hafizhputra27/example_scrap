import pandas as pd

df = pd.read_csv("harga_sibapokting.csv")

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
df_clean = df_clean.sort_values(["tanggal", "pasar", "komoditas"]).reset_index(drop=True)

df_clean.to_csv("harga_sayur_bersih.csv", index=False)
print("Selesai. Total baris:", len(df_clean))