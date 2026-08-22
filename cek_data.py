import pandas as pd
from scraper_sibapokting import get_initial_state, fetch_harga_by_date, parse_table

# --- Bagian 1: validasi CSV hasil scraping ---
df = pd.read_csv("harga_sibapokting.csv")

print("Jumlah pasar unik:", df["pasar"].nunique())          # harusnya 9
print("Jumlah komoditas unik:", df["komoditas"].nunique())  # harusnya 87
print("Jumlah tanggal unik:", df["tanggal"].nunique())       # harusnya 7
print("Persentase data kosong:", df["harga"].isna().mean() * 100, "%")

# --- Bagian 2: cek batas data historis ---
csrf_token, snapshot = get_initial_state()
html_table = fetch_harga_by_date(csrf_token, snapshot, "2024-01-01")
df_test = parse_table(html_table, "2024-01-01")
print(df_test["harga"].notna().sum(), "dari", len(df_test), "komoditas ada datanya di 2024-01-01")

print("\n=== Persentase kosong per pasar ===")
print(df.groupby("pasar")["harga"].apply(lambda x: x.isna().mean() * 100).sort_values(ascending=False))

print("\n=== Persentase kosong per komoditas (10 terburuk) ===")
print(df.groupby("komoditas")["harga"].apply(lambda x: x.isna().mean() * 100).sort_values(ascending=False).head(10))

print("\n=== Tren kosong per bulan ===")
df["tanggal"] = pd.to_datetime(df["tanggal"])
df["bulan"] = df["tanggal"].dt.to_period("M")
print(df.groupby("bulan")["harga"].apply(lambda x: x.isna().mean() * 100))

sayuran_kandidat = [
    "BAYAM", "KANGKUNG", "PAKCOY", "SAWI PUTIH", "SAYURAN TOMAT", "TOMAT HIJAU",
    "TIMUN", "SAYURAN BUNCIS", "KACANG PANJANG", "JAGUNG MANIS",
    "CABE MERAH KERITING", "CABE MERAH TANJUNG", "CABE MERAH TW",
    "CABE RAWIT HIJAU", "CABE RAWIT MERAH", "CABE HIJAU BIASA",
    "SAYURAN KENTANG LOKAL", "KENTANG DIENG", "SAYURAN KOL/KUBIS", "SAYURAN WORTEL",
    "BAWANG MERAH", "BAWANG PUTIH BIASA", "BAWANG DAUN",
]

df_sayur = df[df["komoditas"].isin(sayuran_kandidat)]
print("\n=== Persentase kosong khusus kandidat sayuran (urut terbaik) ===")
print(df_sayur.groupby("komoditas")["harga"].apply(lambda x: x.isna().mean() * 100).sort_values())

print("\n=== Kalau Pasar Cileunyi dikecualikan, berapa persen kosong sisanya? ===")
df_tanpa_cileunyi = df[df["pasar"] != "Pasar Cileunyi"]
print(df_tanpa_cileunyi["harga"].isna().mean() * 100, "%")