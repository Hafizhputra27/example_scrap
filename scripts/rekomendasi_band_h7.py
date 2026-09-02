"""
Price recommendation berbasis distribusi empiris pergerakan harga (BUKAN
prediksi ML titik) -- pivot setelah investigasi membuktikan model ML tidak
bisa mengalahkan persistence di horizon 1-7 hari, tapi fitur Lebaran punya
sinyal nyata untuk BESARAN pergerakan (bukan titik presisi).

Pendekatan: karakterisasi rentang pergerakan harga yang biasa terjadi
(kuantil historis dari dataset_fitur_h7.csv), dipisah kondisi normal vs
dekat Lebaran. Ini jujur ke petani -- "harga biasanya bergerak segini",
bukan pura-pura presisi yang sudah terbukti tidak tercapai.

Catatan konvensi: hari_ke_lebaran_target di sini POSITIF = sebelum Lebaran
(hari menuju Lebaran), NEGATIF = sesudah. (Beda tanda dari kolom
hari_ke_lebaran versi feature_engineering.py -- keduanya konsisten internal,
tapi worth diseragamkan nanti.)
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

df = pd.read_csv(DATA_PROCESSED / "dataset_fitur_h7.csv", parse_dates=["tanggal", "tanggal_target"])
df["delta_pct_7hr"] = (df["harga_target"] - df["harga"]) / df["harga"] * 100

# dekat Lebaran = 21 hari sebelum s/d 7 hari sesudah (run-up + efek langsung)
df["dekat_lebaran"] = df["hari_ke_lebaran_target"].between(-7, 21)

def hitung_band(group):
    return pd.Series({
        "n": len(group),
        "p10": group["delta_pct_7hr"].quantile(0.10),
        "p25": group["delta_pct_7hr"].quantile(0.25),
        "median": group["delta_pct_7hr"].median(),
        "p75": group["delta_pct_7hr"].quantile(0.75),
        "p90": group["delta_pct_7hr"].quantile(0.90),
    })

band_normal = (
    df[~df["dekat_lebaran"]].groupby("komoditas", observed=True)
    .apply(hitung_band, include_groups=False).reset_index()
)
band_normal["kondisi"] = "normal"

band_lebaran = (
    df[df["dekat_lebaran"]].groupby("komoditas", observed=True)
    .apply(hitung_band, include_groups=False).reset_index()
)
band_lebaran["kondisi"] = "dekat_lebaran"

band_all = pd.concat([band_normal, band_lebaran], ignore_index=True).sort_values(["komoditas", "kondisi"])
print(band_all.to_string(index=False))

output_path = MODELS_DIR / "band_rekomendasi_7hari.csv"
band_all.to_csv(output_path, index=False)
print(f"\nDisimpan ke {output_path}")


def rekomendasi(komoditas, harga_sekarang, dekat_lebaran=False):
    """Rekomendasi sederhana berbasis band empiris -- logika keputusan,
    bukan model ML baru, sesuai desain awal di plan.md."""
    kondisi = "dekat_lebaran" if dekat_lebaran else "normal"
    baris = band_all[(band_all["komoditas"] == komoditas) & (band_all["kondisi"] == kondisi)]
    if baris.empty:
        return "Data historis tidak cukup untuk komoditas ini."
    b = baris.iloc[0]
    harga_p10 = harga_sekarang * (1 + b["p10"] / 100)
    harga_median = harga_sekarang * (1 + b["median"] / 100)
    harga_p90 = harga_sekarang * (1 + b["p90"] / 100)

    if b["median"] > 3:
        saran = "Pertimbangkan TUNGGU -- historis harga cenderung naik di kondisi ini."
    elif b["median"] < -3:
        saran = "Pertimbangkan JUAL SEKARANG -- historis harga cenderung turun di kondisi ini."
    else:
        saran = "Harga relatif stabil secara historis -- waktu jual tidak banyak berpengaruh."

    return (
        f"Estimasi harga 7 hari lagi (dari {int(b['n'])} data historis, kondisi '{kondisi}'): "
        f"Rp {harga_p10:,.0f} - Rp {harga_p90:,.0f} (median Rp {harga_median:,.0f}).\n{saran}"
    )


print("\n=== Contoh pemakaian ===")
print(rekomendasi("CABE MERAH KERITING", harga_sekarang=35000, dekat_lebaran=True))
