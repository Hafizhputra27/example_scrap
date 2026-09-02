"""
Kumpulkan semua data + hasil model jadi folder JSON yang dibaca dashboard
(project terpisah). Semua statis -- jalankan ulang kalau data/model berubah.

Output: dashboard_data/
  meta.json      -- tanggal data terakhir, daftar pasar/komoditas + kategori, catatan
  harga.json     -- time series harga harian, per komoditas > per pasar (array 731 nilai)
  cuaca.json     -- curah hujan & suhu harian, per pasar
  kurs.json      -- kurs USD/IDR harian
  prediksi.json  -- prediksi forward H+1/H+3/H+7 (dari predict_forward.py)
  backtest.json  -- model vs aktual vs baseline di periode test (H+7)
  band.json      -- band rekomendasi p10-median-p90, normal vs dekat Lebaran
  riset.json     -- ringkasan 8 tahap eksperimen + angka + kesimpulan

Prasyarat: jalankan dulu feature_engineering, train_model_horizon 7,
predict_forward, rekomendasi_band_h7.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "processed"
MODELS = BASE / "models"
OUT = BASE / "dashboard_data"
OUT.mkdir(exist_ok=True)

KATEGORI = {
    "BAWANG DAUN": "bawang", "BAWANG MERAH": "bawang", "BAWANG PUTIH BIASA": "bawang",
    "BAWANG SUMENEP": "bawang", "BAWANG BOMBAY": "bawang", "BAWANG MERAH BATU": "bawang",
    "CABE MERAH TANJUNG": "cabai", "CABE MERAH KERITING": "cabai", "CABE HIJAU BIASA": "cabai",
    "CABE RAWIT HIJAU": "cabai", "CABE RAWIT MERAH": "cabai",
    "SAYURAN BUNCIS": "sayuran", "SAYURAN TOMAT": "sayuran", "SAYURAN KOL/KUBIS": "sayuran",
    "SAYURAN WORTEL": "sayuran", "TOMAT HIJAU": "sayuran", "JAGUNG MANIS": "sayuran",
    "KENTANG DIENG": "umbi", "SAYURAN KENTANG LOKAL": "umbi", "KETELA POHON": "umbi",
    "UBI JALAR PUTIH": "umbi",
    "KACANG HIJAU": "kacang", "KACANG TANAH KUPAS": "kacang",
    "JERUK": "buah", "PISANG": "buah",
}

CAVEAT_KOMODITAS = ["BAWANG MERAH BATU", "SAYURAN KENTANG LOKAL", "KACANG TANAH KUPAS"]


def tulis(nama, obj):
    path = OUT / nama
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    print(f"  {nama}  ({path.stat().st_size / 1024:.0f} KB)")


def none_if_nan(x):
    return None if pd.isna(x) else (int(round(x)) if abs(x) >= 1 else round(float(x), 2))


# ---------------------------------------------------------------- harga + meta
harga = pd.read_csv(DATA / "harga_sayur_bersih.csv", parse_dates=["tanggal"])
tanggal_awal = harga["tanggal"].min()
tanggal_akhir = harga["tanggal"].max()
semua_tgl = pd.date_range(tanggal_awal, tanggal_akhir, freq="D")
pasar_list = sorted(harga["pasar"].unique())
kom_list = sorted(harga["komoditas"].unique())

harga_json = {"tanggal_awal": tanggal_awal.strftime("%Y-%m-%d"),
              "n_hari": len(semua_tgl), "komoditas": {}}
for kom in kom_list:
    sub = harga[harga["komoditas"] == kom]
    per_pasar = {}
    for ps in pasar_list:
        s = sub[sub["pasar"] == ps].set_index("tanggal")["harga"].reindex(semua_tgl)
        per_pasar[ps] = [none_if_nan(v) for v in s]
    harga_json["komoditas"][kom] = per_pasar
tulis("harga.json", harga_json)

tulis("meta.json", {
    "tanggal_data_terakhir": tanggal_akhir.strftime("%Y-%m-%d"),
    "tanggal_data_awal": tanggal_awal.strftime("%Y-%m-%d"),
    "jumlah_baris": int(len(harga)),
    "pasar": pasar_list,
    "komoditas": [{"nama": k, "kategori": KATEGORI.get(k, "?"),
                   "caveat_data": k in CAVEAT_KOMODITAS} for k in kom_list],
    "catatan": [
        "Prediksi model dihitung dari tanggal data terakhir, BUKAN dari hari ini "
        "(SIBAPOKTING tidak menyediakan API, data harga di-scrape manual).",
        "Harga = harga pasar tradisional tingkat eceran, acuan/referensi untuk petani "
        "menegosiasikan harga jual -- bukan harga pasti dari tengkulak.",
        "Model ML prediksi harga TIDAK mengalahkan baseline persistence di horizon "
        "manapun (1-7 hari). Ditampilkan sebagai pembanding, bukan angka otoritatif.",
        f"3 komoditas ({', '.join(CAVEAT_KOMODITAS)}) punya 1-3 pasar yang jarang lapor; "
        "sebagian sel pasar x komoditas tidak punya prediksi.",
    ],
})

# ---------------------------------------------------------------- cuaca
cuaca = pd.read_csv(DATA / "cuaca_9_pasar.csv", parse_dates=["tanggal"])
cuaca_json = {"tanggal_awal": tanggal_awal.strftime("%Y-%m-%d"), "pasar": {}}
for ps in pasar_list:
    s = cuaca[cuaca["pasar"] == ps].set_index("tanggal").reindex(semua_tgl)
    cuaca_json["pasar"][ps] = {
        "curah_hujan_mm": [none_if_nan(v) for v in s["curah_hujan_mm"]],
        "suhu_avg": [none_if_nan(v) for v in s["suhu_avg"]],
        "suhu_min": [none_if_nan(v) for v in s["suhu_min"]],
        "suhu_max": [none_if_nan(v) for v in s["suhu_max"]],
    }
tulis("cuaca.json", cuaca_json)

# ---------------------------------------------------------------- kurs
kurs = pd.read_csv(DATA / "kurs_usd_idr.csv", parse_dates=["tanggal"]).set_index("tanggal")
kurs = kurs.reindex(semua_tgl)["kurs_usd_idr"]
tulis("kurs.json", {"tanggal_awal": tanggal_awal.strftime("%Y-%m-%d"),
                    "kurs_usd_idr": [none_if_nan(v) for v in kurs]})

# ---------------------------------------------------------------- prediksi forward
pf = pd.read_csv(MODELS / "prediksi_forward.csv")
tulis("prediksi.json", {
    "tanggal_anchor_range": [pf["tanggal_anchor"].min(), pf["tanggal_anchor"].max()],
    "baris": pf.to_dict(orient="records"),
})

# ---------------------------------------------------------------- backtest H+7
h7 = pd.read_csv(DATA / "dataset_fitur_h7.csv", parse_dates=["tanggal", "tanggal_target"])
h7["pasar"] = h7["pasar"].astype("category")
h7["komoditas"] = h7["komoditas"].astype("category")
FEAT = [
    "pasar", "komoditas", "harga_lag1", "harga_lag7", "harga_lag14",
    "harga_rolling7_mean", "harga_rolling7_std", "harga_rolling14_mean",
    "curah_hujan_mm", "suhu_avg", "suhu_max", "suhu_min",
    "curah_hujan_7hr", "curah_hujan_14hr", "kurs_usd_idr", "kurs_lag7",
    "hari_dalam_minggu_target", "bulan_target", "is_weekend_target", "hari_ke_lebaran_target",
]
cut = h7["tanggal_target"].max() - pd.Timedelta(days=60)
test = h7[h7["tanggal_target"] > cut].copy()
booster7 = lgb.Booster(model_file=str(MODELS / "model_direct_h7.txt"))
test["pred"] = test["harga"].to_numpy() + booster7.predict(test[FEAT])

bt = {"horizon": 7, "komoditas": {}}
for kom, gk in test.groupby("komoditas", observed=True):
    per_pasar = {}
    for ps, g in gk.groupby("pasar", observed=True):
        g = g.sort_values("tanggal_target")
        per_pasar[str(ps)] = {
            "tanggal": [d.strftime("%Y-%m-%d") for d in g["tanggal_target"]],
            "aktual": [int(round(v)) for v in g["harga_target"]],
            "model": [int(round(v)) for v in g["pred"]],
            "baseline": [int(round(v)) for v in g["harga"]],
        }
    bt["komoditas"][str(kom)] = per_pasar
tulis("backtest.json", bt)

# ---------------------------------------------------------------- band rekomendasi
band = pd.read_csv(MODELS / "band_rekomendasi_7hari.csv")
band_json = {"horizon": 7, "komoditas": {}}
for kom, g in band.groupby("komoditas"):
    band_json["komoditas"][kom] = {
        row["kondisi"]: {k: round(float(row[k]), 1) for k in ["p10", "p25", "median", "p75", "p90", "lebar_band"]}
        | {"n": int(row["n"])}
        for _, row in g.iterrows()
    }
tulis("band.json", band_json)

# ---------------------------------------------------------------- ringkasan riset
rh = pd.read_csv(MODELS / "ringkasan_horizon.csv")
mh = pd.read_csv(MODELS / "hasil_evaluasi_multi_horizon.csv")
riset = {
    "tahapan": [
        {"n": 1, "judul": "Bug data kotor ditemukan & diperbaiki",
         "isi": "Model awal 11,6x lebih buruk dari baseline -- ternyata data harga mengandung typo entri dari sumber (mis. CABE Rp 50.000.000). ~44 baris (25 komoditas) di-NaN-kan, mengelompok di 2 pasar. Setelah bersih MAE turun drastis."},
        {"n": 2, "judul": "Target framing & objective (L1 collapse)",
         "isi": "Mengubah target ke delta + objective L1 bikin model 'menyamai' baseline -- tapi ternyata collapse jadi persistence murni (delta=0), bukan skill."},
        {"n": 3, "judul": "Model L2 kalah konsisten di H+1/H+2/H+3 (recursive)",
         "isi": "Model yang benar-benar memprediksi tetap kalah dari baseline di semua horizon. Dua bukti independen -> harga ~random walk di horizon pendek."},
        {"n": 4, "judul": "Klasifikasi arah juga gagal",
         "isi": "Reframing regresi -> klasifikasi (naik/turun/stabil) tidak mengalahkan baseline 'selalu stabil'. Wrong-direction rate ~coin-flip."},
        {"n": 5, "judul": "Cabai-only: hipotesis pooling ditolak",
         "isi": "Isolasi ke 5 komoditas paling volatil MEMPERBURUK hasil, bukan memperbaiki."},
        {"n": 6, "judul": "Fitur Lebaran + window test yang benar",
         "isi": "hari_ke_lebaran membawa sinyal nyata, tapi baru tervalidasi setelah test window mencakup Lebaran. Efek Lebaran = ramp musiman multi-minggu, bukan lonjakan harian."},
        {"n": 7, "judul": "Direct model apple-to-apple H+1/H+3/H+7",
         "isi": "Menyamakan metodologi (semua direct) mengungkap 'gap menyempit' sebelumnya sebagian besar artefak metodologi. Model tidak pernah menang."},
        {"n": 8, "judul": "Lebaran-window H+7 + robustness 2 tahun",
         "isi": "Gap terkecil (~10%) muncul di kondisi Lebaran, fitur Lebaran membantu ~5-7%. Tapi robustness check: pergeseran median CABE MERAH TANJUNG hanya di 2026 -- non-robust, sample-of-1."},
    ],
    "horizon_direct": rh.to_dict(orient="records"),
    "horizon_recursive": mh[["horizon", "mae_model", "mae_baseline"]].round(0).to_dict(orient="records"),
    "kesimpulan": (
        "Fitur yang tersedia (harga historis, cuaca, kurs, kalender/Lebaran) tidak cukup "
        "untuk mengalahkan baseline persistence naif di horizon manapun yang diuji (1-7 hari). "
        "Efek musiman nyata tapi muncul di lebar sebaran (ketidakpastian), bukan di titik "
        "tengah -- model ML dilatih mengejar titik tengah, jadi sinyal itu tidak jadi prediksi "
        "yang lebih baik. Rekomendasi harga dibangun dari distribusi empiris (band), bukan ML."
    ),
}
tulis("riset.json", riset)

print(f"\nSelesai. {len(list(OUT.glob('*.json')))} file di {OUT.relative_to(BASE)}/")
