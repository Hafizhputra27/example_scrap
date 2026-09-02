"""
Gabungkan 3 sumber data jadi satu tabel panel siap dipakai untuk feature engineering.

Logika join:
- harga (tanggal, pasar, komoditas, harga) <- ini basis utama, satu baris per kombinasi
- cuaca (tanggal, pasar, ...) <- join by [tanggal, pasar], karena cuaca sama untuk semua komoditas di pasar yang sama
- kurs (tanggal, ...) <- join by [tanggal] saja, karena kurs sama untuk semua pasar & komoditas

Hasil akhir: jumlah baris tetap sama seperti harga (98.685), tapi sekarang
setiap baris punya kolom tambahan curah hujan, suhu, dan kurs.
"""

from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"

harga = pd.read_csv(PROCESSED / "harga_sayur_bersih.csv", parse_dates=["tanggal"])
cuaca = pd.read_csv(PROCESSED / "cuaca_9_pasar.csv", parse_dates=["tanggal"])
kurs = pd.read_csv(PROCESSED / "kurs_usd_idr.csv", parse_dates=["tanggal"])

print("Ukuran sebelum digabung:")
print("  harga:", harga.shape)
print("  cuaca:", cuaca.shape)
print("  kurs :", kurs.shape)

# join harga + cuaca berdasarkan tanggal & pasar
df = harga.merge(cuaca, on=["tanggal", "pasar"], how="left")

# join hasilnya + kurs berdasarkan tanggal saja
df = df.merge(kurs, on="tanggal", how="left")

df = df.sort_values(["tanggal", "pasar", "komoditas"]).reset_index(drop=True)

print("\nUkuran setelah digabung:", df.shape)
print("(harusnya baris sama dengan data harga -- 98685)")

print("\nCek data kosong per kolom:")
print(df.isna().sum())

output_path = PROCESSED / "dataset_gabungan.csv"
df.to_csv(output_path, index=False)
print(f"\nDisimpan ke {output_path}")
print()
print(df.head(20).to_string())