"""
Fetch data kurs USD/IDR historis dari Frankfurter API.
https://frankfurter.dev

Gratis, tanpa API key, berbasis data European Central Bank sejak 1999.
Cuma update di hari kerja pasar finansial -- weekend/libur diisi
lewat forward-fill (pakai nilai hari kerja terakhir).
"""

from pathlib import Path

import requests
import pandas as pd

BASE_URL = "https://api.frankfurter.dev/v1"
PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"


def fetch_kurs_range(start_date, end_date, output_path=PROCESSED / "kurs_usd_idr.csv"):
    """Ambil kurs USD/IDR untuk satu rentang tanggal sekaligus (satu request)."""
    url = f"{BASE_URL}/{start_date}..{end_date}"
    params = {"from": "USD", "to": "IDR"}

    resp = requests.get(url, params=params, timeout=(10, 90))
    resp.raise_for_status()
    data = resp.json()

    rows = [
        {"tanggal": tanggal, "kurs_usd_idr": nilai["IDR"]}
        for tanggal, nilai in data["rates"].items()
    ]
    df = pd.DataFrame(rows)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df = df.sort_values("tanggal").reset_index(drop=True)

    print(f"Data mentah dari API: {len(df)} baris (cuma hari kerja pasar finansial)")

    # isi hari weekend/libur dengan forward-fill, biar setiap tanggal di rentang
    # start-end punya nilai kurs (dicocokkan nanti dengan data harga harian)
    full_range = pd.date_range(start_date, end_date, freq="D")
    df = (
        df.set_index("tanggal")
        .reindex(full_range)
        .rename_axis("tanggal")
        .reset_index()
    )
    df["kurs_usd_idr"] = df["kurs_usd_idr"].ffill()

    n_missing_at_start = df["kurs_usd_idr"].isna().sum()
    if n_missing_at_start > 0:
        print(f"Peringatan: {n_missing_at_start} baris di awal masih kosong (belum ada nilai kurs untuk di-forward-fill)")

    df.to_csv(output_path, index=False)
    print(f"Selesai. Total baris setelah forward-fill: {len(df)}. Disimpan ke {output_path}")
    return df


if __name__ == "__main__":
    start = "2024-08-22"
    end = "2026-08-22"

    df = fetch_kurs_range(start, end)
    print(df.head(10))
    print(df.tail(10))