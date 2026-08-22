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