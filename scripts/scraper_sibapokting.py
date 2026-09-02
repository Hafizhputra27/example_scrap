"""
Scraper untuk SIBAPOKTING (Harga Pangan Harian Kabupaten Bandung)
https://sibapokting.bandungkab.go.id/harian

Cara kerja:
1. GET halaman awal -> ambil CSRF token + Livewire snapshot
2. POST ke /livewire/update dengan snapshot itu + tanggal yang diinginkan
3. Parse HTML tabel dari response -> ubah jadi data panel (long format)
4. Ulangi untuk setiap tanggal dalam rentang yang diinginkan

PENTING: jalankan script ini di environment kamu sendiri (Jupyter/Colab/laptop),
bukan di sandbox Claude, karena sandbox Claude tidak punya akses ke domain ini.
"""

import requests
import re
import html as html_module
import pandas as pd
from io import StringIO
from datetime import date, timedelta
from pathlib import Path
import time

BASE_URL = "https://sibapokting.bandungkab.go.id"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
})


def get_initial_state():
    """Ambil halaman awal untuk dapat CSRF token dan Livewire snapshot."""
    resp = session.get(f"{BASE_URL}/harian")
    resp.raise_for_status()
    page_html = resp.text

    csrf_match = re.search(r'name="csrf-token" content="([^"]+)"', page_html)
    if not csrf_match:
        raise RuntimeError("CSRF token tidak ditemukan di halaman. Struktur halaman mungkin berubah.")
    csrf_token = csrf_match.group(1)

    snapshot_match = re.search(r'wire:snapshot="([^"]+)"', page_html)
    if not snapshot_match:
        raise RuntimeError("Livewire snapshot tidak ditemukan. Struktur halaman mungkin berubah.")
    snapshot = html_module.unescape(snapshot_match.group(1))

    return csrf_token, snapshot


def fetch_harga_by_date(csrf_token, snapshot, tanggal_str):
    """Kirim update Livewire untuk tanggal tertentu, dapatkan HTML tabel baru."""
    payload = {
        "_token": csrf_token,
        "components": [
            {
                "snapshot": snapshot,
                "updates": {"end": tanggal_str},
                "calls": [],
            }
        ],
    }
    resp = session.post(
        f"{BASE_URL}/livewire/update",
        json=payload,
        headers={"X-Livewire": "true"},
    )
    resp.raise_for_status()
    data = resp.json()
    html_table = data["components"][0]["effects"]["html"]
    return html_table


def parse_table(html_table, tanggal_str):
    """Ubah HTML tabel jadi DataFrame long format (satu baris = satu harga)."""
    tables = pd.read_html(StringIO(html_table))
    df = tables[0]
    df = df.drop(columns=["Jumlah Pasar", "Rata-Rata"], errors="ignore")

    df_long = df.melt(id_vars="Nama Komoditas", var_name="pasar", value_name="harga_raw")
    df_long["tanggal"] = tanggal_str

    df_long["harga"] = (
        df_long["harga_raw"]
        .astype(str)
        .str.replace("Rp.", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df_long["harga"] = pd.to_numeric(df_long["harga"], errors="coerce")

    df_long = df_long.rename(columns={"Nama Komoditas": "komoditas"})
    return df_long[["tanggal", "pasar", "komoditas", "harga"]]


def scrape_range(start_date, end_date, delay_seconds=1.5, save_every=10, output_path=RAW / "harga_sibapokting.csv"):
    """Scrape rentang tanggal, simpan progresif biar aman kalau terputus di tengah jalan."""
    csrf_token, snapshot = get_initial_state()

    all_data = []
    current = start_date
    n_days = (end_date - start_date).days + 1
    day_count = 0

    while current <= end_date:
        tanggal_str = current.strftime("%Y-%m-%d")
        day_count += 1
        print(f"[{day_count}/{n_days}] Mengambil {tanggal_str}...")

        try:
            html_table = fetch_harga_by_date(csrf_token, snapshot, tanggal_str)
            df = parse_table(html_table, tanggal_str)
            all_data.append(df)
        except Exception as e:
            print(f"  Gagal ambil {tanggal_str}: {e}")

        # simpan progresif tiap `save_every` hari, biar kalau terputus nggak hilang semua
        if day_count % save_every == 0 and all_data:
            pd.concat(all_data, ignore_index=True).to_csv(output_path, index=False)
            print(f"  -> disimpan sementara ke {output_path}")

        current += timedelta(days=1)
        time.sleep(delay_seconds)  # jeda sopan ke server

    final_df = pd.concat(all_data, ignore_index=True)
    final_df.to_csv(output_path, index=False)
    print(f"\nSelesai. Total baris: {len(final_df)}. Disimpan ke {output_path}")
    return final_df


if __name__ == "__main__":
    start = date(2024, 8, 22)
    end = date(2026, 8, 22)

    df = scrape_range(start, end)
    print(df.head(20))