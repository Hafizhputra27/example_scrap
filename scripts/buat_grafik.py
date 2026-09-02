"""
Template pembuat grafik untuk skripsi -- generate PNG dari semua sumber data.

CARA PAKAI:
  python3 scripts/buat_grafik.py            # buat SEMUA grafik ke folder grafik/
  python3 scripts/buat_grafik.py kurs       # buat satu grafik saja (nama fungsi tanpa 'grafik_')
  python3 scripts/buat_grafik.py harga_pasar kurs   # beberapa sekaligus

Tiap grafik = satu fungsi grafik_<nama>(). Untuk bikin grafik baru: copy salah
satu fungsi, ganti isinya, tambahkan ke dict GRAFIK di bawah.

KNOB matplotlib yang sering dipakai:
  plt.subplots(figsize=(lebar_inci, tinggi_inci))   -> ukuran kanvas
  fig.savefig(path, dpi=150)                          -> resolusi (150 cukup buat cetak)
  fig.savefig(path.with_suffix('.svg'))              -> vektor (skala tanpa pecah)
  ax.set_title / set_xlabel / set_ylabel / legend    -> label
"""

import sys
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")            # simpan ke file, tidak buka window
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "processed"
MODELS = BASE / "models"
OUT = BASE / "grafik"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "font.size": 10, "axes.grid": True, "grid.alpha": 0.3})

def _rupiah(ax):
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"Rp {v:,.0f}"))

def _simpan(fig, nama):
    path = OUT / f"{nama}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  tersimpan: {path.relative_to(BASE)}")


# ----------------------------------------------------------------------
def grafik_harga_pasar():
    """Tren harga 1 komoditas di 9 pasar (ganti KOMODITAS untuk yang lain)."""
    KOMODITAS = "CABE MERAH KERITING"
    df = pd.read_csv(DATA / "harga_sayur_bersih.csv", parse_dates=["tanggal"])
    df = df[df["komoditas"] == KOMODITAS]
    fig, ax = plt.subplots(figsize=(13, 6))
    for pasar, g in df.groupby("pasar"):
        ax.plot(g["tanggal"], g["harga"], lw=1, label=pasar)
    ax.set_title(f"Tren Harga {KOMODITAS} di 9 Pasar (Agu 2024 – Agu 2026)")
    ax.set_xlabel("Tanggal"); ax.set_ylabel("Harga"); _rupiah(ax)
    ax.legend(fontsize=8, ncol=3)
    _simpan(fig, "harga_pasar")


def grafik_harga_semua_komoditas():
    """Rata-rata harga per komoditas across 9 pasar, semua komoditas."""
    df = pd.read_csv(DATA / "harga_sayur_bersih.csv", parse_dates=["tanggal"])
    rata = df.groupby(["tanggal", "komoditas"])["harga"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(13, 7))
    for kom, g in rata.groupby("komoditas"):
        ax.plot(g["tanggal"], g["harga"], lw=0.9, label=kom)
    ax.set_title("Rata-rata Harga per Komoditas (9 pasar) – 15 komoditas")
    ax.set_xlabel("Tanggal"); ax.set_ylabel("Harga rata-rata"); _rupiah(ax)
    ax.legend(fontsize=7, ncol=3, loc="upper left")
    _simpan(fig, "harga_semua_komoditas")


def grafik_cuaca_vs_harga():
    """Curah hujan (batang) + harga (garis) untuk 1 pasar + 1 komoditas."""
    PASAR, KOMODITAS = "Pasar Baleendah", "SAYURAN TOMAT"
    harga = pd.read_csv(DATA / "harga_sayur_bersih.csv", parse_dates=["tanggal"])
    cuaca = pd.read_csv(DATA / "cuaca_9_pasar.csv", parse_dates=["tanggal"])
    h = harga[(harga["pasar"] == PASAR) & (harga["komoditas"] == KOMODITAS)]
    c = cuaca[cuaca["pasar"] == PASAR]

    fig, ax1 = plt.subplots(figsize=(13, 6))
    ax1.bar(c["tanggal"], c["curah_hujan_mm"], width=1.0, color="#2980b9", alpha=0.4, label="curah hujan (mm)")
    ax1.set_ylabel("Curah hujan (mm/hari)", color="#2980b9")
    ax2 = ax1.twinx(); ax2.grid(False)
    ax2.plot(h["tanggal"], h["harga"], color="#c0392b", lw=1.3, label="harga")
    ax2.set_ylabel("Harga", color="#c0392b"); _rupiah(ax2)
    ax1.set_title(f"Curah Hujan vs Harga {KOMODITAS} – {PASAR}")
    ax1.set_xlabel("Tanggal")
    _simpan(fig, "cuaca_vs_harga")


def grafik_kurs():
    """Tren kurs USD/IDR."""
    df = pd.read_csv(DATA / "kurs_usd_idr.csv", parse_dates=["tanggal"])
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(df["tanggal"], df["kurs_usd_idr"], color="#16a085", lw=1.2)
    ax.set_title("Kurs USD/IDR (Frankfurter API, forward-filled)")
    ax.set_xlabel("Tanggal"); ax.set_ylabel("Rp per 1 USD"); _rupiah(ax)
    _simpan(fig, "kurs")


def grafik_band_rekomendasi():
    """Band p10–median–p90 pergerakan harga 7-hari per komoditas, normal vs dekat Lebaran."""
    b = pd.read_csv(MODELS / "band_rekomendasi_7hari.csv")
    kom = sorted(b["komoditas"].unique())
    y = range(len(kom))
    fig, ax = plt.subplots(figsize=(11, 8))
    for off, kondisi, warna in [(-0.18, "normal", "#2980b9"), (0.18, "dekat_lebaran", "#c0392b")]:
        sub = b[b["kondisi"] == kondisi].set_index("komoditas").reindex(kom)
        ax.hlines([i + off for i in y], sub["p10"], sub["p90"], color=warna, lw=4, alpha=0.5,
                  label=f"{kondisi} (p10–p90)")
        ax.plot(sub["median"], [i + off for i in y], "o", color=warna, ms=5)
    ax.set_yticks(list(y)); ax.set_yticklabels(kom)
    ax.axvline(0, color="#333", lw=0.8, ls="--")
    ax.set_xlabel("Perubahan harga 7 hari ke depan (%)")
    ax.set_title("Band Rekomendasi: sebaran pergerakan harga 7-hari per komoditas")
    ax.legend()
    _simpan(fig, "band_rekomendasi")


def grafik_mae_horizon():
    """MAE model vs baseline per horizon (dari ringkasan_horizon.csv)."""
    r = pd.read_csv(MODELS / "ringkasan_horizon.csv")
    x = range(len(r)); w = 0.38
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar([i - w/2 for i in x], r["mae_model"], w, label="model", color="#c0392b")
    ax.bar([i + w/2 for i in x], r["mae_baseline"], w, label="baseline persistence", color="#2980b9")
    for i, row in r.iterrows():
        ax.text(i, row["mae_model"], f" +{row['selisih_pct']:.0f}%", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(list(x)); ax.set_xticklabels([f"H+{h}" for h in r["horizon"]])
    ax.set_ylabel("MAE"); _rupiah(ax)
    ax.set_title("Model direct vs Baseline per Horizon")
    ax.legend()
    _simpan(fig, "mae_horizon")


GRAFIK = {
    "harga_pasar": grafik_harga_pasar,
    "harga_semua_komoditas": grafik_harga_semua_komoditas,
    "cuaca_vs_harga": grafik_cuaca_vs_harga,
    "kurs": grafik_kurs,
    "band_rekomendasi": grafik_band_rekomendasi,
    "mae_horizon": grafik_mae_horizon,
}

if __name__ == "__main__":
    pilih = sys.argv[1:] or list(GRAFIK)
    for nama in pilih:
        if nama not in GRAFIK:
            print(f"  ! tidak ada grafik '{nama}'. Pilihan: {', '.join(GRAFIK)}")
            continue
        print(f"buat {nama} ...")
        GRAFIK[nama]()
    print(f"\nSelesai. Cek folder: {OUT.relative_to(BASE)}/")
