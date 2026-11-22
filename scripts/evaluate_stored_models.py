"""
Hitung ulang MAE model TERSIMPAN pada jendela test saat ini -> models/ringkasan_horizon.csv.

Kenapa terpisah dari training: jalur cepat (`run_pipeline.sh --cepat`) tidak melatih
ulang model, jadi angka MAE tidak boleh ikut berubah tanpa modelnya berubah. Script ini
membuat `ringkasan_horizon.csv` selalu berasal dari model yang benar-benar ada di
`models/model_direct_h*.txt` dan jendela test yang sekarang dipakai pipeline.

Rumus, kolom, dan pembulatan identik dengan train_model_horizon.py supaya angka kedua
jalur bisa dibandingkan langsung.

Pemakaian:
    python3 scripts/evaluate_stored_models.py [horizon ...]
"""

import sys
from pathlib import Path

import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "processed"
MODELS = BASE / "models"

HORIZONS = (1, 3, 7)
TEST_DAYS = 60

FEATURE_COLS = [
    "pasar", "komoditas",
    "harga_lag1", "harga_lag7", "harga_lag14",
    "harga_rolling7_mean", "harga_rolling7_std", "harga_rolling14_mean",
    "curah_hujan_mm", "suhu_avg", "suhu_max", "suhu_min",
    "curah_hujan_7hr", "curah_hujan_14hr",
    "kurs_ret_7", "kurs_ret_30",
    "hari_dalam_minggu_target", "bulan_target", "is_weekend_target",
    "is_lebaran_window_target", "hari_sejak_lebaran_target",
]


def evaluasi_horizon(horizon: int) -> dict:
    """MAE model_direct_h{horizon}.txt pada jendela test 60 hari terakhir."""
    path = DATA / f"dataset_fitur_h{horizon}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} belum ada — jalankan scripts/build_dataset_horizon.py {horizon}"
        )

    df = pd.read_csv(path, parse_dates=["tanggal", "tanggal_target"])
    df["pasar"] = df["pasar"].astype("category")
    df["komoditas"] = df["komoditas"].astype("category")

    booster = lgb.Booster(model_file=str(MODELS / f"model_direct_h{horizon}.txt"))
    cut = df["tanggal_target"].max() - pd.Timedelta(days=TEST_DAYS)
    test = df[df["tanggal_target"] > cut]

    pred = test["harga"].to_numpy() + booster.predict(test[FEATURE_COLS])
    y = test["harga_target"]
    mae_model = mean_absolute_error(y, pred)
    mae_baseline = mean_absolute_error(y, test["baseline_hN"])

    return {
        "horizon": horizon,
        "mae_model": round(mae_model),
        "mape_model": round(mean_absolute_percentage_error(y, pred) * 100, 2),
        "mae_baseline": round(mae_baseline),
        "mape_baseline": round(
            mean_absolute_percentage_error(y, test["baseline_hN"]) * 100, 2
        ),
        "selisih_pct": round((mae_model / mae_baseline - 1) * 100, 1),
        "n_baris": int(len(test)),
    }


def tulis_ringkasan(rows: list[dict]) -> None:
    kolom = ["horizon", "mae_model", "mape_model", "mae_baseline", "mape_baseline", "selisih_pct"]
    out = pd.DataFrame(rows)[kolom].sort_values("horizon")
    out.to_csv(MODELS / "ringkasan_horizon.csv", index=False)


def main() -> None:
    diminta = [int(a) for a in sys.argv[1:]] or list(HORIZONS)
    rows = [evaluasi_horizon(h) for h in diminta]
    tulis_ringkasan(rows)

    print("=== MAE model tersimpan pada jendela test saat ini ===")
    for r in rows:
        print(f"H+{r['horizon']}  MAE Rp {r['mae_model']:,} vs baseline Rp {r['mae_baseline']:,} "
              f"({r['selisih_pct']:+.1f}%)  |  MAPE {r['mape_model']}%  |  n={r['n_baris']}")
    print(f"ringkasan_horizon.csv diperbarui dari model tersimpan")


if __name__ == "__main__":
    main()
