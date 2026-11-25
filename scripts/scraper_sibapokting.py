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
import sys
import html as html_module
import pandas as pd
from io import StringIO
from datetime import date, timedelta
from pathlib import Path
import time

BASE_URL = "https://sibapokting.bandungkab.go.id"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_HARGA = RAW / "harga_sibapokting.csv"
AWAL_DATA = date(2024, 8, 22)  # awal cakupan data proyek

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
})


PERCOBAAN_MAKS = 3
JEDA_RETRY_AWAL = 2.0  # detik; berlipat dua tiap percobaan (2 s, 4 s)


def _request_dengan_retry(method, url, **kwargs):
    """Request dengan retry pada gangguan sesaat: 5xx (termasuk 526 Cloudflare) dan timeout.

    4xx tidak diulang: itu jawaban pasti server, bukan gangguan sesaat.
    """
    for percobaan in range(1, PERCOBAAN_MAKS + 1):
        try:
            resp = session.request(method, url, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as e:
            galat = f"{type(e).__name__}: {e}"
        else:
            if resp.status_code < 500:
                resp.raise_for_status()
                return resp
            galat = f"HTTP {resp.status_code}"
        if percobaan == PERCOBAAN_MAKS:
            raise RuntimeError(
                f"gagal {method} {url} setelah {PERCOBAAN_MAKS} percobaan: {galat}"
            ) from None
        jeda = JEDA_RETRY_AWAL * (2 ** (percobaan - 1))
        print(f"  {method} {url} -> {galat}; ulangi dalam {jeda:.0f} s "
              f"({percobaan}/{PERCOBAAN_MAKS})", file=sys.stderr)
        time.sleep(jeda)


def get_initial_state():
    """Ambil halaman awal untuk dapat CSRF token dan Livewire snapshot."""
    resp = _request_dengan_retry("GET", f"{BASE_URL}/harian", timeout=45)
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
    resp = _request_dengan_retry(
        "POST",
        f"{BASE_URL}/livewire/update",
        json=payload,
        headers={"X-Livewire": "true"},
        timeout=45,
    )
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


def terakhir_di_raw(path=RAW_HARGA):
    """Tanggal terakhir yang sudah ada di CSV mentah (None kalau file belum ada)."""
    if not Path(path).exists():
        return None
    tgl = pd.read_csv(path, usecols=["tanggal"])["tanggal"]
    return date.fromisoformat(str(tgl.max())[:10]) if len(tgl) else None


def rentang_scrape(terakhir, hari_ini, arg=None):
    """Tanggal mulai & akhir scrape.

    Default: hari setelah data terakhir s/d kemarin, supaya menjalankan file ini
    langsung tidak pernah mengulang rentang mati atau meminta hari yang belum
    terbit. `arg` (YYYY-MM-DD) menimpa batas akhir.
    """
    sampai = date.fromisoformat(arg) if arg else hari_ini - timedelta(days=1)
    mulai = AWAL_DATA if terakhir is None else terakhir + timedelta(days=1)
    return mulai, sampai


def scrape_range(start_date, end_date, delay_seconds=1.5, save_every=10, output_path=RAW_HARGA):
    """Scrape rentang tanggal, simpan progresif biar aman kalau terputus di tengah jalan.

    Hari yang belum terbit (0 harga numerik) dilewati, bukan ditulis sebagai baris NaN.
    """
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
            terisi = int(df["harga"].notna().sum())
            if terisi == 0:
                print(f"  {tanggal_str}: belum terbit (0 harga) — dilewati")
            else:
                all_data.append(df)
                print(f"  {tanggal_str}: {terisi} harga")
        except Exception as e:
            print(f"  Gagal ambil {tanggal_str}: {e}")

        # simpan progresif tiap `save_every` hari, biar kalau terputus nggak hilang semua
        if day_count % save_every == 0 and all_data:
            pd.concat(all_data, ignore_index=True).to_csv(output_path, index=False)
            print(f"  -> disimpan sementara ke {output_path}")

        current += timedelta(days=1)
        time.sleep(delay_seconds)  # jeda sopan ke server

    if not all_data:
        raise ValueError(f"tidak ada hari terbit di {start_date}..{end_date}")
    final_df = pd.concat(all_data, ignore_index=True)
    final_df.to_csv(output_path, index=False)
    print(f"\nSelesai. Total baris: {len(final_df)}. Disimpan ke {output_path}")
    return final_df


def jalankan_manual(arg=None, hari_ini=None):
    """Scrape incremental untuk pemakaian langsung (`python3 scripts/scraper_sibapokting.py`).

    Hasil di-merge ke CSV mentah, bukan menimpa: `scrape_range` sendiri hanya
    menulis rentang yang di-scrape.
    """
    hari_ini = hari_ini or date.today()
    terakhir = terakhir_di_raw()
    mulai, sampai = rentang_scrape(terakhir, hari_ini, arg)
    print(f"range: {mulai}..{sampai} (data mentah terakhir: {terakhir or 'belum ada'})")
    if mulai > sampai:
        print("tidak ada tanggal baru untuk di-scrape")
        return None

    tmp = RAW_HARGA.with_name("_harga_scrape_manual.csv")
    tmp.unlink(missing_ok=True)
    df = scrape_range(mulai, sampai, output_path=tmp)

    lama = pd.read_csv(RAW_HARGA) if RAW_HARGA.exists() else pd.DataFrame(columns=df.columns)
    gabung = (
        pd.concat([lama, df], ignore_index=True)
        .drop_duplicates(subset=["tanggal", "pasar", "komoditas"], keep="last")
        .sort_values(["tanggal", "pasar", "komoditas"])
        .reset_index(drop=True)
    )
    gabung.to_csv(RAW_HARGA, index=False)
    tmp.unlink(missing_ok=True)
    print(f"manual: +{len(gabung) - len(lama)} baris, total {len(gabung)}, "
          f"data terakhir {max(gabung['tanggal'])}")
    return gabung


if __name__ == "__main__":
    try:
        df = jalankan_manual(sys.argv[1] if len(sys.argv) > 1 else None)
    except ValueError as e:
        sys.exit(f"scrape: {e} (tidak ada yang ditulis)")
    if df is not None:
        print(df.head(20))

