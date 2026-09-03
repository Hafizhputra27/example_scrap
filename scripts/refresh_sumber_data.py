"""
Refresh 3 sumber data ke tanggal terbaru, sebelum run_pipeline.sh.

Semua INCREMENTAL + MERGE:
- harga (SIBAPOKTING): scrape hanya tanggal setelah baris terakhir, append+dedupe.
- cuaca (Open-Meteo): fetch hanya rentang baru per pasar, append+dedupe. Kalau
  sebagian pasar gagal fetch, history lama pasar itu tetap dipertahankan.
- kurs (Frankfurter): 1 request full-range (cepat; butuh kontinuitas utk ffill).

Request-nya semua sudah ada timeout (fetch_weather/kurs/scraper) — jadi tidak
akan menggantung. Rentang kecil per run → jarang timeout.

Dipakai oleh .github/workflows/refresh-*.yml. Manual:
    python scripts/refresh_sumber_data.py            # s/d kemarin
    python scripts/refresh_sumber_data.py 2026-09-10 # s/d tanggal tertentu

Exit != 0 hanya kalau scrape HARGA wajib tapi 0 baris (biar workflow gagal keras,
tidak men-deploy data basi). Cuaca/kurs yang gagal sebagian → warning, lanjut.
"""

import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scraper_sibapokting as scraper  # noqa: E402
import fetch_weather  # noqa: E402
import fetch_kurs  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
RAW_HARGA = BASE / "data" / "raw" / "harga_sibapokting.csv"
CUACA = BASE / "data" / "processed" / "cuaca_9_pasar.csv"
AWAL = date(2024, 8, 22)  # awal cakupan data proyek


def _sampai() -> date:
    if len(sys.argv) > 1:
        return date.fromisoformat(sys.argv[1])
    return date.today() - timedelta(days=1)  # kemarin (WIB via env TZ di workflow)


def _tgl_str(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s).dt.strftime("%Y-%m-%d")


def _merge(lama: pd.DataFrame, baru: pd.DataFrame, key: list[str]) -> pd.DataFrame:
    return (
        pd.concat([lama, baru], ignore_index=True)
        .drop_duplicates(subset=key, keep="last")
        .sort_values(key)
        .reset_index(drop=True)
    )


def refresh_harga(sampai: date) -> None:
    key = ["tanggal", "pasar", "komoditas"]
    lama = pd.read_csv(RAW_HARGA)
    lama["tanggal"] = _tgl_str(lama["tanggal"])
    terakhir = date.fromisoformat(max(lama["tanggal"]))
    mulai = terakhir + timedelta(days=1)

    if mulai > sampai:
        print(f"harga: sudah terkini ({terakhir})")
        return

    print(f"harga: scrape {mulai}..{sampai}")
    tmp = RAW_HARGA.with_name("_harga_baru.csv")
    tmp.unlink(missing_ok=True)
    try:
        scraper.scrape_range(mulai, sampai, output_path=tmp)
    except ValueError as e:  # concat kosong = semua hari gagal
        sys.exit(f"harga: scrape GAGAL total ({e})")

    if not tmp.exists():
        sys.exit("harga: scraper tidak menulis file apa pun")

    baru = pd.read_csv(tmp)
    tmp.unlink()
    baru["tanggal"] = _tgl_str(baru["tanggal"])
    if baru.empty:
        sys.exit("harga: 0 baris baru dari scraper")

    gabung = _merge(lama, baru, key)
    gabung.to_csv(RAW_HARGA, index=False)
    print(f"harga: +{len(gabung) - len(lama)} baris, total {len(gabung)} (s/d {max(gabung['tanggal'])})")


def _fetch_pasar(nama, lat, lon, mulai: date, sampai: date, chunk=180, retry=3) -> pd.DataFrame:
    """Fetch cuaca 1 pasar dalam potongan <= `chunk` hari, retry per potongan.

    Open-Meteo archive dari runner CI sering timeout untuk rentang panjang;
    potongan kecil + retry jauh lebih andal. Raise kalau ada potongan yang
    tetap gagal setelah semua retry (caller yang putuskan fatal/tidak)."""
    frames = []
    cur = mulai
    while cur <= sampai:
        end = min(cur + timedelta(days=chunk - 1), sampai)
        for attempt in range(1, retry + 1):
            try:
                frames.append(fetch_weather.fetch_weather_for_pasar(nama, lat, lon, str(cur), str(end)))
                break
            except Exception as e:  # noqa: BLE001
                if attempt == retry:
                    raise
                print(f"    {nama} {cur}..{end} gagal ({attempt}/{retry}: {e}); retry…", file=sys.stderr)
                time.sleep(3 * attempt)
        cur = end + timedelta(days=1)
        time.sleep(0.5)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def refresh_cuaca(sampai: date) -> None:
    key = ["tanggal", "pasar"]
    lama = pd.read_csv(CUACA)
    lama["tanggal"] = _tgl_str(lama["tanggal"])
    last_per_pasar = lama.groupby("pasar")["tanggal"].max().to_dict()

    frames, gagal = [], []
    for nama, (lat, lon) in fetch_weather.PASAR_KOORDINAT.items():
        last = last_per_pasar.get(nama)
        mulai = AWAL if last is None else date.fromisoformat(last) + timedelta(days=1)
        if mulai > sampai:
            continue
        tag = "backfill" if last is None else "incr"
        print(f"cuaca [{tag}] {nama}: {mulai}..{sampai}")
        try:
            df = _fetch_pasar(nama, lat, lon, mulai, sampai)
            if not df.empty:
                frames.append(df)
        except Exception as e:  # noqa: BLE001
            gagal.append(nama)
            print(f"cuaca: {nama} GAGAL total ({e}) — history lama dipertahankan", file=sys.stderr)

    if not frames:
        msg = "cuaca: tidak ada data baru"
        if gagal:
            msg += f" | PERINGATAN gagal: {gagal}"
        print(msg, file=sys.stderr if gagal else sys.stdout)
        return

    baru = pd.concat(frames, ignore_index=True)
    baru["tanggal"] = _tgl_str(baru["tanggal"])
    gabung = _merge(lama, baru, key)
    gabung.to_csv(CUACA, index=False)
    tail = f" | PERINGATAN gagal (menyusul run berikutnya): {gagal}" if gagal else ""
    print(f"cuaca: +{len(gabung) - len(lama)} baris, total {len(gabung)}, "
          f"{gabung['pasar'].nunique()}/9 pasar{tail}")


def refresh_kurs(sampai: date) -> None:
    print(f"kurs: fetch {AWAL}..{sampai}")
    try:
        fetch_kurs.fetch_kurs_range(str(AWAL), str(sampai))
    except Exception as e:  # noqa: BLE001
        print(f"kurs: fetch gagal ({e}) — pertahankan data lama", file=sys.stderr)


def main() -> None:
    sampai = _sampai()
    print(f"=== refresh sumber data s/d {sampai} ===")
    refresh_harga(sampai)
    refresh_cuaca(sampai)
    refresh_kurs(sampai)
    print("=== selesai refresh sumber data ===")


if __name__ == "__main__":
    main()
