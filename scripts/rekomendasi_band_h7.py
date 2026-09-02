"""
Price recommendation berbasis distribusi empiris pergerakan harga (BUKAN
prediksi ML titik) -- pivot setelah investigasi membuktikan model ML tidak
bisa mengalahkan persistence di horizon 1-7 hari.

Temuan kunci yang membentuk desain ini: efek Lebaran nyata secara empiris,
tapi muncul di EKOR distribusi (varians/ketidakpastian), bukan di median
untuk sebagian besar komoditas. Ini kenapa model ML gagal (dia mengejar
titik tengah, padahal yang berubah adalah lebar sebarannya) -- dan kenapa
logika rekomendasi WAJIB mempertimbangkan lebar band, bukan cuma median.

PERBAIKAN dari versi sebelumnya: rekomendasi() sekarang eksplisit
memperhitungkan lebar band (p90-p10). Versi awal pernah bilang "harga
stabil" untuk kasus dengan band Rp 24.500-48.000 (~35%) hanya karena
median-nya 0% -- itu menyesatkan. Ditambah peringatan sampel kecil untuk
kondisi dekat_lebaran (cuma 2 event Lebaran di data, pola beda antar tahun --
lihat cek_robustness_lebaran.py).

Konvensi: hari_ke_lebaran_target POSITIF = sebelum Lebaran, NEGATIF = sesudah.
Window "dekat Lebaran" = 21 hari sebelum s/d 7 hari sesudah (menangkap run-up).
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

df = pd.read_csv(DATA_PROCESSED / "dataset_fitur_h7.csv", parse_dates=["tanggal", "tanggal_target"])
df["delta_pct_7hr"] = (df["harga_target"] - df["harga"]) / df["harga"] * 100
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
band_all["lebar_band"] = band_all["p90"] - band_all["p10"]

output_path = MODELS_DIR / "band_rekomendasi_7hari.csv"
band_all.to_csv(output_path, index=False)
print(f"Band tersimpan ke {output_path}")
print(band_all[["komoditas", "kondisi", "n", "p10", "median", "p90", "lebar_band"]].round(1).to_string(index=False))


def rekomendasi(komoditas, harga_sekarang, dekat_lebaran=False):
    """Logika keputusan berbasis band empiris -- SEKARANG mempertimbangkan
    lebar band, bukan cuma median."""
    kondisi = "dekat_lebaran" if dekat_lebaran else "normal"
    baris = band_all[(band_all["komoditas"] == komoditas) & (band_all["kondisi"] == kondisi)]
    if baris.empty:
        return "Data historis tidak cukup untuk komoditas ini."
    b = baris.iloc[0]
    lebar = b["lebar_band"]
    harga_p10 = harga_sekarang * (1 + b["p10"] / 100)
    harga_median = harga_sekarang * (1 + b["median"] / 100)
    harga_p90 = harga_sekarang * (1 + b["p90"] / 100)

    if b["median"] > 3:
        arah = "median historis cenderung NAIK"
    elif b["median"] < -3:
        arah = "median historis cenderung TURUN"
    else:
        arah = "median historis relatif stabil"

    if lebar > 30:
        catatan_ketidakpastian = "Ketidakpastian TINGGI -- rentang sangat lebar, median saja tidak cukup mewakili."
        saran = "Waktu jual sulit dioptimalkan dari data historis saja di kondisi ini -- pertimbangkan faktor lain (kebutuhan modal, kapasitas simpan hasil panen)."
    elif lebar > 15:
        catatan_ketidakpastian = "Ketidakpastian sedang -- perhatikan rentangnya, jangan cuma patokan ke median."
        saran = ("Pertimbangkan TUNGGU (dengan waspada)." if b["median"] > 3
                 else "Pertimbangkan JUAL SEKARANG (dengan waspada)." if b["median"] < -3
                 else "Harga cenderung stabil, tapi tetap ada variasi -- waktu jual tidak terlalu krusial.")
    else:
        catatan_ketidakpastian = "Ketidakpastian relatif rendah -- median cukup representatif."
        saran = ("Pertimbangkan TUNGGU." if b["median"] > 3
                 else "Pertimbangkan JUAL SEKARANG." if b["median"] < -3
                 else "Harga stabil -- waktu jual tidak banyak berpengaruh.")

    peringatan_sampel = ""
    if kondisi == "dekat_lebaran":
        peringatan_sampel = (
            "\nPERINGATAN: estimasi kondisi Lebaran ini cuma didasarkan pada 2 kejadian "
            "dalam data (Lebaran 2025 & 2026) -- sampel sangat kecil untuk pola musiman, "
            "dan beberapa komoditas menunjukkan pola berbeda antara kedua tahun itu "
            "(lihat cek_robustness_lebaran.py). Anggap sebagai indikasi awal, bukan pola pasti."
        )

    return (
        f"Estimasi harga 7 hari lagi (dari {int(b['n'])} data historis, kondisi '{kondisi}'): "
        f"Rp {harga_p10:,.0f} - Rp {harga_p90:,.0f} (median Rp {harga_median:,.0f}, {arah}).\n"
        f"{catatan_ketidakpastian}\n{saran}{peringatan_sampel}"
    )


print("\n=== Contoh: CABE MERAH KERITING dekat Lebaran (kasus yang sebelumnya menyesatkan) ===")
print(rekomendasi("CABE MERAH KERITING", harga_sekarang=35000, dekat_lebaran=True))
print("\n=== Contoh: CABE MERAH TANJUNG dekat Lebaran (satu-satunya yang median-nya bergeser) ===")
print(rekomendasi("CABE MERAH TANJUNG", harga_sekarang=80000, dekat_lebaran=True))
