"""
Fetch data cuaca historis dari Open-Meteo untuk 9 pasar di Kabupaten Bandung.
https://open-meteo.com/en/docs/historical-weather-api

Gratis, tanpa API key. Fitur yang diambil: curah hujan, suhu rata-rata/min/max.
Kelembaban (humidity) tidak tersedia sebagai agregat harian di Open-Meteo,
jadi belum dimasukkan di sini -- bisa ditambah nanti lewat data per jam kalau perlu.
"""

from pathlib import Path
import time

import requests
import pandas as pd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"

PASAR_KOORDINAT = {
    "Pasar Margahayu": (-6.975223, 107.561626),
    "Pasar Ciwidey": (-7.099343, 107.469491),
    "Pasar Baleendah": (-6.999283, 107.628376),
    "Pasar Stasiun Majalaya": (-7.049224, 107.760320),
    "Pasar Baru Majalaya": (-7.049110, 107.763372),
    "Pasar Sehat Cicalengka": (-6.990657, 107.841555),
    "Pasar Cileunyi": (-6.941148, 107.753259),
    "Pasar Banjaran": (-7.048782, 107.587726),
    "Pasar Sehat Soreang": (-7.028647, 107.520496),
}

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_weather_for_pasar(nama_pasar, lat, lon, start_date, end_date):
    """Ambil cuaca historis untuk satu pasar, satu rentang tanggal."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,temperature_2m_mean,temperature_2m_max,temperature_2m_min",
        "timezone": "Asia/Jakarta",
    }
    resp = requests.get(BASE_URL, params=params)
    resp.raise_for_status()
    data = resp.json()

    df = pd.DataFrame(data["daily"])
    df = df.rename(columns={
        "time": "tanggal",
        "precipitation_sum": "curah_hujan_mm",
        "temperature_2m_mean": "suhu_avg",
        "temperature_2m_max": "suhu_max",
        "temperature_2m_min": "suhu_min",
    })
    df["pasar"] = nama_pasar
    return df[["tanggal", "pasar", "curah_hujan_mm", "suhu_avg", "suhu_max", "suhu_min"]]


def fetch_all_pasar(start_date, end_date, output_path=PROCESSED / "cuaca_9_pasar.csv"):
    """Loop semua 9 pasar, gabungkan jadi satu CSV."""
    all_data = []
    for i, (nama_pasar, (lat, lon)) in enumerate(PASAR_KOORDINAT.items(), start=1):
        print(f"[{i}/{len(PASAR_KOORDINAT)}] Mengambil cuaca untuk {nama_pasar}...")
        try:
            df = fetch_weather_for_pasar(nama_pasar, lat, lon, start_date, end_date)
            all_data.append(df)
        except Exception as e:
            print(f"  Gagal ambil {nama_pasar}: {e}")
        time.sleep(1)  # jeda sopan ke server

    final_df = pd.concat(all_data, ignore_index=True)
    final_df.to_csv(output_path, index=False)
    print(f"\nSelesai. Total baris: {len(final_df)}. Disimpan ke {output_path}")
    return final_df


if __name__ == "__main__":
    start = "2024-08-22"
    end = "2026-08-22"

    df = fetch_all_pasar(start, end)
    print(df.head(20))