# PRD — Dashboard Informasi Harga Hasil Bumi Kabupaten Bandung

**Status:** draft untuk direview
**Tanggal:** 2026-09-03
**Pemilik:** Hafizh (skripsi — prediksi harga sayur)
**Repo data (sumber):** `example_scrap` → menghasilkan `dashboard_data/*.json`
**Repo dashboard:** **project terpisah** (mis. `~/Documents/GitHub/dashboard-harga-sayur/`), tidak disatukan dengan repo data.

---

## 1. Ringkasan

Dashboard web statis (JavaScript, tanpa build tooling) yang menampilkan:

1. **Eksplorasi data historis 2 tahun** — harga 25 komoditas di 9 pasar tradisional, cuaca 9 lokasi, kurs USD/IDR.
2. **Prediksi model ML** — backtest (historis) + prediksi ke depan (H+1/H+3/H+7), **selalu berdampingan dengan baseline** dan label kejujuran.
3. **Rekomendasi berbasis band empiris** — rentang pergerakan harga 7 hari (p10–median–p90), normal vs menjelang Lebaran.
4. **Ringkasan riset** — 8 tahap investigasi model + kesimpulan.

Tujuan tahun ini: **dashboard informasi** yang bisa ditunjukkan ke dosen/stakeholder. Tahun depan: aplikasi dengan fitur rekomendasi (di luar scope PRD ini).

## 2. Konteks & prinsip (WAJIB dipatuhi)

Fase riset membuktikan: **model ML tidak mengalahkan baseline persistence naif ("harga besok ≈ harga hari ini") di horizon manapun 1–7 hari.** Efek musiman nyata tapi muncul di *lebar sebaran* (ketidakpastian), bukan di *titik tengah*.

Konsekuensi untuk dashboard:

| Prinsip | Implementasi |
|---|---|
| Prediksi model **tidak pernah** tampil sendirian | Setiap angka prediksi model dirender berpasangan dengan baseline + label `model +X% MAE` |
| Jujur soal tanggal | Prediksi "dari tanggal data terakhir" (bukan hari ini). Banner tanggal data selalu terlihat. |
| Harga = acuan, bukan harga pasti | Disebutkan di footer/tooltip: harga pasar eceran, bukan harga dari tengkulak |
| Ketidakpastian adalah pesan utama | Signature visual = "pita ketidakpastian" (lihat design doc) |
| Data pasar tidak lengkap | 3 komoditas (Bawang Merah Batu, Sayuran Kentang Lokal, Kacang Tanah Kupas) ditandai; sel pasar×komoditas kosong ditampilkan "data tidak tersedia", bukan disembunyikan diam-diam |

## 3. Pengguna & use case

| Pengguna | Kebutuhan |
|---|---|
| Dosen penguji / pembimbing | Melihat cakupan data, memverifikasi metodologi & kesimpulan riset secara visual |
| Peneliti (Hafizh) | Ambil figur untuk bab hasil; cek konsistensi data |
| (Nanti) Dinas / stakeholder pangan | Gambaran tren harga & volatilitas per komoditas/pasar |

Bukan untuk: petani langsung (itu aplikasi tahun depan), transaksi, input data.

## 4. Sumber data — kontrak `dashboard_data/*.json`

Dashboard **hanya** membaca file JSON statis ini (di-generate `scripts/export_dashboard.py` di repo data). Tidak ada backend, tidak ada fetch API eksternal.

| File | Isi | Ukuran | Skema |
|---|---|---|---|
| `meta.json` | tanggal data terakhir/awal, daftar 9 pasar, 25 komoditas `{nama, kategori, caveat_data}`, catatan[] | 2 KB | objek |
| `harga.json` | `{tanggal_awal, n_hari, komoditas:{<nama>:{<pasar>:[harga/null × n_hari]}}}` | ~920 KB | array padat per (komoditas,pasar), indeks = offset hari dari `tanggal_awal` |
| `cuaca.json` | `{tanggal_awal, pasar:{<pasar>:{curah_hujan_mm[], suhu_avg[], suhu_min[], suhu_max[]}}}` | 77 KB | sama pola |
| `kurs.json` | `{tanggal_awal, kurs_usd_idr:[nilai × n_hari]}` | 4 KB | array |
| `prediksi.json` | `{tanggal_anchor_range, baris:[{pasar, komoditas, tanggal_anchor, harga_terakhir, tanggal_target_h{1,3,7}, pred_model_h{1,3,7}, pred_baseline_h{1,3,7}, mae_model_hist_h{1,3,7}, mae_baseline_hist_h{1,3,7}, model_lebih_buruk_pct_h{1,3,7}}]}` (224 baris) | 132 KB | tabel |
| `backtest.json` | `{horizon:7, komoditas:{<nama>:{<pasar>:{tanggal[], aktual[], model[], baseline[]}}}}` (periode test 60 hari) | 360 KB | seri per (komoditas,pasar) |
| `band.json` | `{horizon:7, komoditas:{<nama>:{normal:{p10,p25,median,p75,p90,lebar_band,n}, dekat_lebaran:{...}}}}` | 5 KB | objek |
| `riset.json` | `{tahapan:[{n,judul,isi}], horizon_direct:[], horizon_recursive:[], kesimpulan}` | 3 KB | objek |

**Regenerasi:** `./run_pipeline.sh` di repo data → salin folder `dashboard_data/` ke project dashboard. Untuk auto-refresh nanti: script scraper dijadwalkan → `run_pipeline.sh` → deploy ulang. Tidak dibangun sekarang.

## 5. Fitur & section

Satu halaman scroll dengan navigasi anchor. Section:

### 5.1 Hero — "Pita Ketidakpastian"
- Chart lebar 1 komoditas unggulan (default: **Cabe Merah Keriting** — volatil, dikenal) sepanjang 2 tahun: garis harga + pita p10–p90 (dari band).
- Judul-tesis (1 kalimat): *"Yang bisa diprediksi dari harga sayur bukan angka pastinya, tapi seberapa lebar kemungkinannya bergerak."*
- 3 angka pendukung (bukan hero): jumlah komoditas (25), pasar (9), rentang data (24 bln).

### 5.2 Eksplorasi Harga
- Pemilih komoditas (dropdown/grup kategori: bawang, cabai, sayuran, umbi, kacang, buah).
- Pemilih pasar: default **"rentang 9 pasar"** (envelope min–max + garis rata-rata). Bisa spotlight 1 pasar (garis tebal warna hijau, envelope jadi abu).
- Rentang waktu: 3 bln / 1 thn / 2 thn (default 2 thn).
- Statistik: harga terakhir, min/max/median periode, % hari data kosong.
- Badge caveat kalau komoditas termasuk 3 yang bermasalah datanya.
- Hover: crosshair + tooltip (tanggal, harga per pasar terpilih).

### 5.3 Cuaca & Kurs
- **Curah hujan** — bar chart harian per pasar terpilih (2 thn).
- **Suhu** — line chart (avg, dengan pita min–max) per pasar terpilih. Chart TERPISAH dari curah hujan (tidak dual-axis).
- **Kurs USD/IDR** — line chart 2 thn, 1 seri.
- Catatan: fitur cuaca & kurs **tidak menambah akurasi prediksi harga** di horizon yang diuji (tautkan ke section riset).

### 5.4 Prediksi Model
- **Backtest** (per komoditas×pasar terpilih): line chart periode test 60 hari — 3 seri: `aktual` (ink, tebal), `model` (amber), `baseline` (abu, putus-putus). MAE model & baseline ditampilkan sebagai teks.
- **Prediksi ke depan** (tabel/kartu): untuk komoditas terpilih, 9 pasar × {H+1, H+3, H+7}. Tiap sel: kartu-berpasangan `model` vs `baseline` + label `model historis +X% MAE`.
- Banner: *"Prediksi dihitung dari data terakhir <tanggal>. Model ML secara historis kurang akurat dibanding baseline — ditampilkan sebagai pembanding."*
- **Bar chart MAE model vs baseline per horizon** (dari `riset.json` horizon_direct).

### 5.5 Rekomendasi (Band Empiris)
- Untuk komoditas terpilih: visualisasi band p10–median–p90, **normal vs dekat Lebaran** berdampingan (2 baris atau overlay).
- Kalkulator sederhana: input "harga sekarang" → output rentang estimasi 7 hari + teks rekomendasi (logika dari `rekomendasi_band_h7.py` — pertimbangkan lebar band, bukan cuma median; peringatan sampel kecil untuk kondisi Lebaran).
- Chart "lebar band per komoditas" (semua 25, normal vs Lebaran) — menunjukkan komoditas mana yang paling/tidak fluktuatif.

### 5.6 Ringkasan Riset
- 8 tahap dari `riset.json` sebagai daftar bernomor (di sini penomoran *memang* sekuens — tiap tahap membangun di atas sebelumnya).
- Tabel horizon (direct + recursive): model vs baseline.
- Blok kesimpulan.

## 6. Non-fungsional

| Aspek | Target |
|---|---|
| Hosting | File statis. Bisa dibuka `file://` atau di-serve (`python3 -m http.server`), atau deploy ke GitHub Pages / Netlify (drag-drop). |
| Build tooling | **Tidak ada.** ES modules native, `<script type="module">`. Tidak ada npm/bundler. |
| Dependency | **Nol runtime dependency.** Chart = inline SVG buatan sendiri (helper module). Font = Google Fonts (diizinkan) dengan fallback stack. |
| Ukuran load awal | < 1,5 MB (JSON) + < 100 KB kode. `harga.json` & `backtest.json` di-fetch lazy saat section-nya terlihat. |
| Responsif | Mobile → desktop. Chart scroll horizontal dalam container sendiri kalau sempit; body tidak pernah scroll horizontal. |
| Aksesibilitas | Fokus keyboard terlihat; `prefers-reduced-motion` dihormati; setiap chart punya alternatif tabel; identitas seri tidak hanya lewat warna (legend + label langsung). |
| Tema | Light + dark, mengikuti `prefers-color-scheme` + toggle manual. Hijau (lihat design doc). |
| Bahasa | Indonesia. |
| Browser | Evergreen (Chrome/Firefox/Safari terbaru). |

## 7. Struktur project dashboard (usulan)

```
dashboard-harga-sayur/
├── index.html
├── style.css
├── data/                     # salinan dashboard_data/*.json dari repo data
├── src/
│   ├── main.js                # bootstrap, routing anchor, lazy-load section
│   ├── store.js               # fetch + cache JSON, helper tanggal (offset → Date)
│   ├── chart/
│   │   ├── svg.js             # primitif: skala, sumbu, path, crosshair, tooltip
│   │   ├── line.js            # line + pita (band/envelope)
│   │   ├── bars.js            # bar (curah hujan, MAE)
│   │   └── band.js            # band p10–p90 (signature)
│   ├── sections/
│   │   ├── hero.js
│   │   ├── harga.js
│   │   ├── cuaca-kurs.js
│   │   ├── prediksi.js
│   │   ├── rekomendasi.js
│   │   └── riset.js
│   └── components/
│       ├── prediksi-chip.js   # kartu berpasangan model|baseline
│       ├── tabel-view.js      # alternatif tabel untuk tiap chart
│       └── selector.js        # pemilih komoditas/pasar/rentang
├── docs/                      # PRD + design (dari sini)
└── README.md
```

## 8. Di luar scope

- Backend / database / API.
- Auto-scraping & auto-refresh (dirancang agar bisa ditambahkan; tidak dibangun).
- Autentikasi, multi-user, komentar.
- Prediksi > H+7 atau > 3 hari ke depan real-time.
- Rekomendasi berbasis ML (sudah terbukti tidak lebih baik dari band empiris).
- Komoditas di luar 25 (beras, daging, sayuran daun dengan data 69% kosong).
- Fitur mobile-app / PWA offline.

## 9. Tahapan implementasi

1. **Kerangka** — `index.html`, `style.css` (token dari design doc), `store.js`, navigasi anchor, dark/light toggle.
2. **Modul chart SVG** — `svg.js` primitif + `line.js` (paling banyak dipakai). Uji dengan `kurs.json` (paling sederhana).
3. **Section Eksplorasi Harga** — selector + line/envelope + tabel-view. Ini section terbesar; kalau pola ini beres, sisanya mengikuti.
4. **Section Hero** — pita ketidakpastian (reuse `band.js`).
5. **Section Cuaca & Kurs** — `bars.js` + line.
6. **Section Prediksi** — backtest chart + `prediksi-chip` + bar MAE.
7. **Section Rekomendasi** — band viz + kalkulator + lebar-band chart.
8. **Section Ringkasan Riset** — sebagian besar teks + 1 tabel.
9. **Pass aksesibilitas & responsif** — tabel-view semua chart, fokus, reduced-motion, uji mobile.
10. **Deploy** — GitHub Pages / Netlify.

## 10. Kriteria selesai (Definition of Done)

- [ ] Semua 8 file JSON terbaca; tidak ada error console.
- [ ] Setiap prediksi model tampil berpasangan baseline + label MAE.
- [ ] Banner tanggal data terakhir selalu terlihat.
- [ ] 3 komoditas caveat & sel kosong ditandai eksplisit.
- [ ] Setiap chart punya alternatif tabel + legend/label (bukan warna-saja).
- [ ] Light & dark tema; `prefers-reduced-motion` dihormati.
- [ ] Responsif 360px → desktop; body tidak scroll horizontal.
- [ ] Bisa dibuka tanpa server (atau dengan `http.server`), tanpa build step.
