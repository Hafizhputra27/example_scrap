# MODEL-CONTRACT — prediksi harga sayur PATANI

Status: putusan eksperimen HAG-42, 2026-11-22. Data `data/processed/dataset_fitur.csv`
s/d 2026-11-21 (821 hari × 9 pasar × 25 komoditas, SIBAPOKTING). Semua angka di bawah
dihasilkan oleh `scripts/evaluate_walkforward.py` → `models/hasil_evaluasi_walkforward.csv`
(120 baris: 3 varian × direct H+1..H+7 + recursive H+1..H+3 × 4 fold).

## 1. Baseline

Baseline = **persistence**: prediksi harga H hari ke depan = harga anchor hari ini,
tanpa koreksi. Tidak ada parameter, tidak dilatih, dan tidak pernah diubah definisinya
selama eksperimen. Model dan baseline dievaluasi pada baris yang sama.

Split: walk-forward 4 fold × 60 hari pada `tanggal_target`
(2026-03-26 → 2026-05-25, → 2026-07-24, → 2026-09-22, → 2026-11-21). Train per fold
hanya memuat `tanggal_target` sebelum fold, dengan embargo = horizon; data test tidak
masuk training. "Menang" = MAE **dan** MAPE model < baseline pada walk-forward, bukan
satu jendela.

## 2. Putusan

**LightGBM kalah dari persistence di semua horizon. Persistence adalah prediktor titik
resmi.** Ringkasan selisih MAE rata-rata 4 fold (positif = model kalah):

| Horizon | direct, fitur produksi | direct, fitur L1 | direct, L2 (winsor+L1+gate) |
|---|---|---|---|
| H+1 | +42,4% | +34,2% | 0,00% (seri) |
| H+2 | +35,3% | +33,2% | +0,05% |
| H+3 | +31,9% | +28,2% | +0,11% |
| H+4 | +31,1% | +25,5% | +0,86% |
| H+5 | +27,8% | +20,5% | +4,60% |
| H+6 | +25,7% | +18,4% | +2,86% |
| H+7 | +20,2% | +17,3% | +6,52% |

Recursive H+1..H+3: +85,6 / +86,0 / +80,4% (fitur produksi), +45,6 / +41,1 / +35,1% (L1),
0,00% (L2 = baseline persis). Tidak ada satu pun horizon yang memenuhi definisi menang.

## 3. Tabel selisih per fold

Direct, selisih MAE % (positif = kalah). Kolom fold 1–4; tiap sel `produksi / L1 / L2`.

| Horizon | fold 1 | fold 2 | fold 3 | fold 4 |
|---|---|---|---|---|
| H+1 | 59,2 / 44,0 / 0,0 | 35,4 / 28,5 / 0,0 | 31,4 / 39,3 / 0,0 | 43,8 / 24,9 / 0,0 |
| H+2 | 38,9 / 40,3 / 0,0 | 37,3 / 24,0 / 0,0 | 32,7 / 45,5 / +0,2 | 32,2 / 23,0 / +0,1 |
| H+3 | 38,3 / 29,5 / 0,0 | 30,9 / 17,4 / +0,1 | 28,8 / 43,4 / +0,2 | 29,7 / 22,4 / +0,1 |
| H+4 | 35,5 / 33,4 / +4,5 | 29,3 / 13,0 / −0,9 | 27,0 / 34,5 / −0,2 | 32,7 / 21,0 / +0,1 |
| H+5 | 31,4 / 24,8 / +9,0 | 24,7 / 7,6 / +0,7 | 26,6 / 28,6 / +8,2 | 28,7 / 21,0 / +0,4 |
| H+6 | 23,4 / 21,1 / +6,5 | 23,6 / 5,4 / −2,8 | 23,3 / 24,1 / +6,3 | 32,7 / 23,0 / +1,5 |
| H+7 | 16,0 / 21,3 / +7,3 | 18,5 / 3,1 / −2,3 | 20,7 / 21,1 / +11,4 | 25,5 / 23,5 / +9,7 |

Recursive, selisih MAE %:

| Horizon | fold 1 | fold 2 | fold 3 | fold 4 |
|---|---|---|---|---|
| H+1 | 162,9 / 55,3 / 0,0 | 75,2 / 39,4 / 0,0 | 46,8 / 58,4 / 0,0 | 57,5 / 29,1 / 0,0 |
| H+2 | 170,8 / 46,5 / 0,0 | 72,0 / 34,5 / 0,0 | 45,4 / 59,0 / 0,0 | 55,9 / 24,3 / 0,0 |
| H+3 | 160,9 / 36,5 / 0,0 | 67,9 / 28,1 / 0,0 | 39,9 / 55,2 / 0,0 | 53,1 / 20,5 / 0,0 |

MAE dan MAPE mentah per sel (bukan hanya selisih) ada di
`models/hasil_evaluasi_walkforward.csv`. Empat fold L2 yang menang MAE: H+4 f2 (−0,89%),
H+4 f3 (−0,15%), H+6 f2 (−2,80%), H+7 f2 (−2,29%). Semuanya di satu rezim waktu (fold 2),
dan dua fold H+1/H+3 dengan λ=1 kalah 5–9%; itu sinyal tidak stabil, bukan fitur kurang.

## 4. Mekanik L2 (dan kenapa hasilnya nol)

1. Target delta diwinsorize p1–p99 pada data train (spike ekor tidak mendominasi L1).
2. Regresi LightGBM objective **L1** (median), 500 trees, lr 0,05, 31 leaves.
3. Gate classifier biner `P(|delta| > q90 train)`; AUC 0,85 pada test (base rate 12%).
4. Prediksi = anchor + λ·delta bila prob ≥ gate, selain itu anchor. λ ∈ {0, .1, .25, .5, 1}
   dan gate ∈ {0, .5, .6, .7, .8, .9} dipilih **hanya** dari validasi internal
   (60 hari terakhir train), tidak pernah dari test.

Hasil: validasi internal memilih **λ = 0** di 5/28 fold direct — artinya model sendiri
menyimpulkan koreksi terbaiknya nol. Di H+1 seluruh fold L2 = baseline persis. Di
H+2/H+3, delta yang dipakai ≤ 0,2% selisih. Recursive: λ=0 atau delta ≈ 0 di 12/12 sel.
Gate tidak menyelamatkan: model bisa mendeteksi **besaran** gerakan besar (AUC 0,85),
tapi arahnya 45% naik / 55% turun — koin.

## 5. Yang masih layak dipakai dari ML

- **Band empiris p10–p90** per komoditas dan kondisi (`models/band_rekomendasi_7hari.csv`,
  sudah dipakai app). Ini yang membawa informasi: lebar sebaran, bukan titik tengah.
- **Probabilitas gerakan besar** (`|delta| > q90`, AUC 0,85) sebagai penanda
  ketidakpastian / peringatan, **bukan** arah atau harga titik.
- Klasifikasi arah H+1 tidak layak: akurasi 0,834 vs baseline kelas mayoritas 0,838.

## 6. Temuan operasional untuk pekerjaan berikutnya

1. **Direct lebih baik dari recursive secara rata-rata pada input yang sama** (per fold
   ada pengecualian kecil, mis. H+3 fold 4). Rata-rata selisih
   (recursive − direct): 43–51 pp dengan fitur produksi, 6,9–11,4 pp dengan fitur L1
   (H+1..H+3). Recursive mengakumulasi error satu model H+1 untuk 2–3 langkah. Produksi
   saat ini melaporkan angka recursive untuk H+2/H+3 (`hasil_evaluasi_multi_horizon.csv`),
   jadi angka yang tampil lebih buruk dari yang bisa dicapai model direct. Keputusan
   mengganti artefak/penyajian itu **belum diambil** (menunggu human); jangan mengubah
   `predict_forward.py` atau kontrak serving tanpa persetujuan.
2. **Fitur time-proxy menambah error.** `kurs_usd_idr` level + `kurs_lag7`, dan
   `hari_ke_lebaran` bertanda (lompat ~354 hari saat Lebaran terdekat berganti, mis.
   2026-09-15), berperilaku sebagai indeks waktu. Menggantinya dengan retur kurs 7/30 hari
   dan event-window Lebaran (`|jarak| ≤ 30`, `hari_sejak_lebaran` cap 90) menurunkan gap
   direct 2,1–8,3 pp (terbesar H+1: 42,4 → 34,2%; H+6: 25,7 → 18,4%). Ini perbaikan nyata
   tapi bukan penyebab utama kekalahan.

## 7. Reproduksi & kontrak artefak

```bash
python3 scripts/evaluate_walkforward.py --semua
# = baseline + l1 + l2 dalam satu CSV (120 baris). Varian tunggal:
#   --varian baseline|l1|l2
```

Varian L1/L2 menghitung fitur kandidat **di dalam harness**; skrip
produksi (`feature_engineering.py`, `build_dataset_horizon.py`, `predict_forward.py`,
`train_*.py`) tidak diubah oleh eksperimen ini.

Artefak produksi tetap: `models/model_h1.txt`, `models/model_direct_h{1,3,7}.txt`,
`models/dataset_fitur*.csv`, `models/hasil_evaluasi_multi_horizon.csv`,
`models/ringkasan_horizon.csv`. File baru `models/hasil_evaluasi_walkforward.csv` adalah
tambahan, bukan pengganti. Pelanggaran definisi baseline (mis. mempermudah baseline) atau
memasukkan data test ke training membatalkan seluruh tabel di atas.

## 8. Batasan

- Hanya 4 fold (8 bulan); bukan bukti untuk horizon musiman lintas tahun.
- Satu wilayah (9 pasar Kabupaten Bandung); jangan klaim provinsi.
- 84,8% delta harian persis nol dan median |delta| = 0; untuk H+1, MAE-optimal memang
  tidak bergerak. Model yang lebih baik butuh sinyal timing yang tidak ada di data ini
  (harga pasar lain sudah diuji: dispersi antar pasar tidak menolong).
