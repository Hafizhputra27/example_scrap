#!/usr/bin/env python3
"""Cek invarian kejujuran MAE (tanpa pytest, tanpa jaringan, tanpa training).

    python3 scripts/test_model_mae_consistency.py

Invarian yang dijaga:
1. `models/ringkasan_horizon.csv` MAE tiap horizon == MAE yang dihitung ulang dari
   `models/model_direct_h{horizon}.txt` pada jendela test saat ini.
2. `models/prediksi_forward.csv` memakai angka MAE yang sama
   (`mae_model_hist_h*` / `mae_baseline_hist_h*`).

Kalau salah satu gagal, app akan menampilkan MAE milik model lain.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_stored_models import MODELS, evaluasi_horizon  # noqa: E402

TOLERANSI = 1  # pembulatan rupiah


def main() -> None:
    ringkasan = pd.read_csv(MODELS / "ringkasan_horizon.csv").set_index("horizon")
    prediksi = pd.read_csv(MODELS / "prediksi_forward.csv")

    for h in (1, 3, 7):
        r = evaluasi_horizon(h)
        tertulis = int(ringkasan.loc[h, "mae_model"])
        assert abs(tertulis - r["mae_model"]) <= TOLERANSI, (
            f"ringkasan h{h}: {tertulis} != model tersimpan {r['mae_model']} "
            f"(selisih {tertulis - r['mae_model']} Rp)"
        )
        basis_tertulis = int(ringkasan.loc[h, "mae_baseline"])
        assert abs(basis_tertulis - r["mae_baseline"]) <= TOLERANSI, (
            f"ringkasan h{h} baseline: {basis_tertulis} != {r['mae_baseline']}"
        )

        col_model, col_basis = f"mae_model_hist_h{h}", f"mae_baseline_hist_h{h}"
        assert col_model in prediksi.columns, f"kolom {col_model} tidak ada"
        nilai = {
            (int(m), int(b))
            for m, b in zip(prediksi[col_model], prediksi[col_basis])
        }
        assert nilai == {(r["mae_model"], r["mae_baseline"])}, (
            f"prediksi_forward h{h}: MAE {sorted(nilai)} != ringkasan/model "
            f"{(r['mae_model'], r['mae_baseline'])}"
        )
        print(f"H+{h}: ringkasan {tertulis:,} / prediksi {r['mae_model']:,} / "
              f"model tersimpan {r['mae_model']:,} -- cocok")

    print("invarian OK")


if __name__ == "__main__":
    main()
