# Auto-refresh pipeline — spec & runbook

**Tujuan:** data + prediksi dashboard [patani-dashboard.vercel.app](https://patani-dashboard.vercel.app)
selalu ~1 hari terkini, tanpa langkah manual.

## Alur

```
cron harian 06:00 WIB (Sen–Sab)          cron mingguan 05:00 WIB (Minggu)
        │                                         │
  refresh_sumber_data.py                    refresh_sumber_data.py
   ├─ scrape SIBAPOKTING (Δ hari, append)    (idem)
   ├─ fetch_weather.py  (full range)
   └─ fetch_kurs.py     (full range)
        │                                         │
  run_pipeline.sh --cepat                   run_pipeline.sh  (latih ulang model)
   → dashboard_data/*.json                   → dashboard_data/*.json + models/*.txt
        │                                         │
  sanity check (meta.tanggal_data_terakhir ≤ 3 hari)
        │
  commit ke example_scrap (data/ models/ dashboard_data/)
        │
  clone patani-dashboard (PAT) → cp *.json public/data/ → commit + push
        │
  Vercel auto-deploy  →  situs update
```

## Komponen

| File | Isi |
|---|---|
| `scripts/refresh_sumber_data.py` | Wrapper: scrape harga **incremental** (hanya tanggal setelah baris terakhir, lalu append + dedupe pada `[tanggal,pasar,komoditas]`); fetch cuaca & kurs **full-range** (timpa). Exit ≠ 0 kalau scrape wajib tapi 0 baris. |
| `.github/workflows/refresh-harian.yml` | cron `0 23 * * 0-5` UTC (= 06:00 WIB Sen–Sab) + `workflow_dispatch`. `run_pipeline.sh --cepat`. |
| `.github/workflows/refresh-mingguan.yml` | cron `0 22 * * 6` UTC (= 05:00 WIB Minggu) + `workflow_dispatch`. `run_pipeline.sh` penuh (latih ulang), commit `models/*.txt` juga. |

`concurrency.group: refresh` → harian & mingguan tidak pernah jalan bersamaan.

## Setup (manual, sekali)

1. **Fine-grained PAT** — github.com/settings/tokens?type=beta → Generate new token
   - Resource owner: `Hafizhputra27`
   - Repository access: **Only select repositories** → `patani-dashboard`
   - Permissions → Repository → **Contents: Read and write**
   - Expiry: 1 tahun (set reminder untuk regenerate)
2. **Simpan sebagai secret** di repo ini: Settings → Secrets and variables → Actions →
   New repository secret → nama `DASHBOARD_PUSH_TOKEN`, value = PAT tadi.
3. Merge branch `auto-refresh`.
4. **Uji manual:** Actions → "refresh harian" → Run workflow. Cek:
   - langkah "Refresh sumber data" sukses (berapa baris baru)
   - `run_pipeline.sh --cepat` sukses, catat **durasi** (untuk kalibrasi timeout)
   - commit muncul di `patani-dashboard` → Vercel deploy → situs `Data s/d <tanggal baru>`
5. Kalau OK, biarkan cron jalan sendiri.

## Yang harus diverifikasi di run pertama (spike)

- **Durasi** `--cepat` (perkiraan <5 mnt) dan penuh (5–20 mnt). Sesuaikan `timeout-minutes`.
- **Weather lag** — Open-Meteo archive telat ~2–5 hari. `combine_data.py` join `how="left"`
  → baris ekor bisa NaN cuaca/kurs. Konfirmasi `feature_engineering.py` & `predict_forward.py`
  tidak error (LightGBM handle NaN; anchor = "baris fitur lengkap terakhir" → mundur sendiri).
  Kalau error: tambahkan forward-fill cuaca di `refresh_sumber_data.py` atau clamp range price ke min(price_last, weather_last).
- **Scraper vs perubahan situs** — kalau regex CSRF / `wire:snapshot` di `scraper_sibapokting.py`
  tak cocok → `RuntimeError` → job gagal (email otomatis). Perbaiki regex, jalankan ulang.

## Estimasi kuota GitHub Actions (private repo, free 2000 mnt/bln)

harian `--cepat` ~5 mnt × ~26 hari = ~130 mnt · mingguan penuh ~20 mnt × 4 = ~80 mnt →
**~210 mnt/bln**. Aman.

## Maintenance

- **`LEBARAN`** hardcoded di `scripts/predict_forward.py` (`["2025-03-31","2026-03-21"]`)
  dan di dashboard `src/lib/proyeksi.js`. **Sebelum Maret 2027** tambahkan `"2027-03-10"`
  (verifikasi tanggal Idul Fitri via SKB 3 Menteri).
- `data/raw/harga_sibapokting.csv` tumbuh ~1MB/tahun (semua 87 komoditas × 9 pasar). Aman bertahun-tahun.
- PAT expiry → regenerate + update secret.

## Kalau pipeline gagal

Data lama tetap tampil di situs (JSON terakhir yang berhasil di-push). Indikator
"proyeksi sudah N hari" / peringatan "> 30 hari" di halaman `#/prediksi` jadi
jaring pengaman: kalau N naik terus, berarti refresh macet — cek tab Actions.
