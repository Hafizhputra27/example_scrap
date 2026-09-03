"""
Refresh 3 sumber data ke tanggal terbaru, sebelum run_pipeline.sh.

- harga (SIBAPOKTING): scrape INCREMENTAL — hanya tanggal setelah baris terakhir
  di data/raw/harga_sibapokting.csv s/d kemarin, lalu append + dedupe.
- cuaca (Open-Meteo) & kurs (Frankfurter): fetch full-range (awal..kemarin),
  timpa file. API-nya cepat & dibangun untuk range; overwrite lebih sederhana
  dan otomatis mengoreksi revisi data historis.

Dipakai oleh .github/workflows/refresh-*.yml. Bisa juga dijalankan manual:
    python scripts/refresh_sumber_data.py            # s/d kemarin
    python scripts/refresh_sumber_data.py 2026-09-10 # s/d tanggal tertentu

Exit code != 0 kalau scrape harga wajib dilakukan tapi tidak menghasilkan baris
apa pun (biar workflow gagal keras, tidak men-deploy data basi).
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scraper_sibapokting as scraper  # noqa: E402
import fetch_weather  # noqa: E402
import fetch_kurs  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
RAW_HARGA = BASE / "data" / "raw" / "harga_sibapokting.csv"
AWAL = date(2024, 8, 22)  # awal cakupan data proyek

KEY = ["tanggal", "pasar", "komoditas"]


def _sampai() -> date:
    if len(sys.argv) > 1:
        return date.fromisoformat(sys.argv[1])
    return date.today() - timedelta(days=1)  # kemarin (WIB via env TZ di workflow)


def refresh_harga(sampai: date) -> None:
    lama = pd.read_csv(RAW_HARGA)
    lama["tanggal"] = pd.to_datetime(lama["tanggal"]).dt.strftime("%Y-%m-%d")
    terakhir = date.fromisoformat(max(lama["tanggal"]))
    mulai = terakhir + timedelta(days=1)

    if mulai > sampai:
        print(f"harga: sudah terkini (data terakhir {terakhir}, target {sampai})")
        return

    print(f"harga: scrape {mulai}..{sampai}")
    tmp = RAW_HARGA.with_name("_harga_baru.csv")
    if tmp.exists():
        tmp.unlink()
    try:
        scraper.scrape_range(mulai, sampai, output_path=tmp)
    except ValueError as e:  # concat kosong = semua hari gagal
        print(f"harga: scrape GAGAL total ({e})", file=sys.stderr)
        sys.exit(1)

    if not tmp.exists():
        print("harga: scraper tidak menulis file apa pun", file=sys.stderr)
        sys.exit(1)

    baru = pd.read_csv(tmp)
    tmp.unlink()
    baru["tanggal"] = pd.to_datetime(baru["tanggal"]).dt.strftime("%Y-%m-%d")
    if baru.empty:
        print("harga: 0 baris baru dari scraper", file=sys.stderr)
        sys.exit(1)

    gabung = (
        pd.concat([lama, baru], ignore_index=True)
        .drop_duplicates(subset=KEY, keep="last")
        .sort_values(KEY)
        .reset_index(drop=True)
    )
    tambahan = len(gabung) - len(lama.drop_duplicates(subset=KEY))
    gabung.to_csv(RAW_HARGA, index=False)
    print(f"harga: +{max(tambahan, 0)} baris, total {len(gabung)} (s/d {max(gabung['tanggal'])})")


def refresh_cuaca_kurs(sampai: date) -> None:
    print(f"cuaca: fetch {AWAL}..{sampai}")
    fetch_weather.fetch_all_pasar(str(AWAL), str(sampai))
    print(f"kurs: fetch {AWAL}..{sampai}")
    fetch_kurs.fetch_kurs_range(str(AWAL), str(sampai))


def main() -> None:
    sampai = _sampai()
    print(f"=== refresh sumber data s/d {sampai} ===")
    refresh_harga(sampai)
    refresh_cuaca_kurs(sampai)
    print("=== selesai refresh sumber data ===")


if __name__ == "__main__":
    main()
