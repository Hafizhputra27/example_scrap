"""
Walk-forward evaluation: 4 fold x 60 hari, model direct H+1..H+7 dan
recursive H+1..H+3, dibandingkan baseline persistence pada baris yang sama.

Tujuan: mengukur "menang" tanpa bergantung pada satu jendela 60 hari terakhir.
Tidak mengubah artefak produksi; keluaran = models/hasil_evaluasi_walkforward.csv.

Pemakaian:
    python3 scripts/evaluate_walkforward.py                 # varian baseline (fitur saat ini)
    python3 scripts/evaluate_walkforward.py --varian l1     # fitur time-proxy dibuang
    python3 scripts/evaluate_walkforward.py --varian l2     # winsorize + L1 + gate (lihat L2)

Konvensi baseline TIDAK diubah: persistence = harga anchor, tanpa koreksi.
Fold memakai tanggal_target; train hanya memuat baris dengan tanggal_target
sebelum fold (embargo = horizon) sehingga data test tidak masuk training.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "processed"
MODELS = BASE / "models"

HORIZON_DIRECT = [1, 2, 3, 4, 5, 6, 7]
HORIZON_RECURSIVE = [1, 2, 3]
FOLD_DAYS = 60
N_FOLD = 4

FEATURES_BASELINE = [
    "pasar", "komoditas",
    "harga_lag1", "harga_lag7", "harga_lag14",
    "harga_rolling7_mean", "harga_rolling7_std", "harga_rolling14_mean",
    "curah_hujan_mm", "suhu_avg", "suhu_max", "suhu_min",
    "curah_hujan_7hr", "curah_hujan_14hr",
    "kurs_usd_idr", "kurs_lag7",
    "hari_dalam_minggu", "bulan", "is_weekend", "hari_ke_lebaran",
]

# L1 mengganti kolom time-proxy (lihat feature_engineering.py)
FEATURES_L1 = [
    "pasar", "komoditas",
    "harga_lag1", "harga_lag7", "harga_lag14",
    "harga_rolling7_mean", "harga_rolling7_std", "harga_rolling14_mean",
    "curah_hujan_mm", "suhu_avg", "suhu_max", "suhu_min",
    "curah_hujan_7hr", "curah_hujan_14hr",
    "kurs_ret_7", "kurs_ret_30",
    "hari_dalam_minggu", "bulan", "is_weekend",
    "is_lebaran_window", "hari_sejak_lebaran",
]

FEATURES_TARGET_BASELINE = [
    "hari_dalam_minggu_target", "bulan_target", "is_weekend_target", "hari_ke_lebaran_target",
]
FEATURES_TARGET_L1 = [
    "hari_dalam_minggu_target", "bulan_target", "is_weekend_target",
    "is_lebaran_window_target", "hari_sejak_lebaran_target",
]


def muat_data(varian):
    df = pd.read_csv(DATA / "dataset_fitur.csv", parse_dates=["tanggal"])
    df = df.sort_values(["pasar", "komoditas", "tanggal"]).reset_index(drop=True)
    for kol in ("pasar", "komoditas"):
        df[kol] = df[kol].astype("category")
    fitur = {"baseline": FEATURES_BASELINE, "l1": FEATURES_L1,
             "l2": FEATURES_L1}[varian]
    fitur_target = {"baseline": FEATURES_TARGET_BASELINE,
                    "l1": FEATURES_TARGET_L1, "l2": FEATURES_TARGET_L1}[varian]
    return df, fitur, fitur_target


LEBARAN = pd.to_datetime(["2025-03-31", "2026-03-21", "2027-03-10"])


def bangun_direct(df, horizon, varian):
    """Frame anchor -> target H hari ke depan (sama dengan build_dataset_horizon.py)."""
    d = df.copy()
    g = d.groupby(["pasar", "komoditas"], observed=True)
    d["harga_target"] = g["harga"].shift(-horizon)
    d["tanggal_target"] = d["tanggal"] + pd.Timedelta(days=horizon)
    tgl = d["tanggal_target"].dt
    d["hari_dalam_minggu_target"] = tgl.dayofweek
    d["bulan_target"] = tgl.month
    d["is_weekend_target"] = tgl.dayofweek.isin([5, 6]).astype(int)
    if varian == "baseline":
        # konvensi produksi saat ini: lebaran - tanggal (positif = sebelum)
        d["hari_ke_lebaran_target"] = [min(((l - t).days for l in LEBARAN), key=abs)
                                       for t in d["tanggal_target"]]
    else:
        _kalender_l1(d, "tanggal_target", "_target")
    d = d.dropna(subset=["harga", "harga_target"]).reset_index(drop=True)
    return d


def _kalender_l1(d, kolom_tanggal, suffix=""):
    """Satu konvensi (L1): hari_sejak_lebaran = hari sejak Lebaran terakhir, 0..90;
    is_lebaran_window = 1 bila |jarak ke Lebaran terdekat| <= 30.
    Tidak ada jarak bertanda -> tidak ada diskontinuitas argmin."""
    t = d[kolom_tanggal]
    sejak = np.full(len(d), 90.0)
    for l in LEBARAN:
        selisih = (t - l).dt.days.to_numpy()
        sejak = np.where((selisih >= 0) & (selisih < sejak), selisih, sejak)
    jarak = np.min(np.abs(np.stack([(t - l).dt.days.to_numpy() for l in LEBARAN])), axis=0)
    d["hari_sejak_lebaran" + suffix] = sejak
    d["is_lebaran_window" + suffix] = (jarak <= 30).astype(int)
    return d


def folds(d, kolom_tanggal, akhir):
    tepi = [akhir - pd.Timedelta(days=FOLD_DAYS * (N_FOLD - i)) for i in range(N_FOLD + 1)]
    out = []
    for i in range(N_FOLD):
        mulai, selesai = tepi[i], tepi[i + 1]
        test = (d[kolom_tanggal] > mulai) & (d[kolom_tanggal] <= selesai)
        out.append((i + 1, mulai, selesai, test))
    return out


def latih(X, y, params=None):
    p = dict(n_estimators=500, learning_rate=0.05, num_leaves=31,
             min_child_samples=50, random_state=42)
    if params:
        p.update(params)
    m = lgb.LGBMRegressor(**p)
    m.fit(X, y, categorical_feature=["pasar", "komoditas"])
    return m


# ----------------------------------------------------------------- L2
# Winsorize delta p1-p99 + objective L1 + gate classifier dua tahap.
# lambda (skala delta) dan gate dipilih HANYA dari validasi internal (60 hari
# terakhir train), supaya test tidak pernah menyetel parameter.
GRID_LAMBDA = [0.0, 0.1, 0.25, 0.5, 1.0]
GRID_GATE = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9]


def latih_l2(train, kol, kol_target, kol_anchor):
    delta = train[kol_target] - train[kol_anchor]
    lo, hi = delta.quantile(0.01), delta.quantile(0.99)
    reg = latih(train[kol], delta.clip(lo, hi), {"objective": "regression_l1"})
    tau = max(float(delta.abs().quantile(0.90)), 1.0)
    cls = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                             min_child_samples=100, random_state=42, verbose=-1)
    cls.fit(train[kol], (delta.abs() > tau).astype(int),
            categorical_feature=["pasar", "komoditas"])
    return {"reg": reg, "cls": cls, "lo": lo, "hi": hi, "tau": tau}


def pilih_l2(bundle, val, kol, kol_target, kol_anchor):
    delta_pred = bundle["reg"].predict(val[kol])
    prob = bundle["cls"].predict_proba(val[kol])[:, 1]
    y = val[kol_target].to_numpy()
    anchor = val[kol_anchor].to_numpy()
    best = (1e18, None, None)
    for lam in GRID_LAMBDA:
        for gate in GRID_GATE:
            aktif = prob >= gate if gate > 0 else np.ones(len(prob), dtype=bool)
            pred = anchor + np.where(aktif, lam * delta_pred, 0.0)
            mae = mean_absolute_error(y, pred)
            if mae < best[0]:
                best = (mae, lam, gate)
    return best[1], best[2]


def terapkan_l2(bundle, frame, kol, kol_anchor, lam, gate):
    delta_pred = bundle["reg"].predict(frame[kol])
    if lam == 0:
        return np.zeros(len(frame))
    if gate > 0:
        prob = bundle["cls"].predict_proba(frame[kol])[:, 1]
        return np.where(prob >= gate, lam * delta_pred, 0.0)
    return lam * delta_pred



def evaluasi(rows, jalur, varian, horizon, fold, mulai, selesai, y, model_pred, baseline_pred,
             lam=None, gate=None):
    y = np.asarray(y)
    model_pred = np.asarray(model_pred)
    baseline_pred = np.asarray(baseline_pred)
    mae_m = mean_absolute_error(y, model_pred)
    mae_b = mean_absolute_error(y, baseline_pred)
    rows.append({
        "varian": varian, "jalur": jalur, "horizon": horizon, "fold": fold,
        "test_start": mulai.date(), "test_end": selesai.date(), "n": len(y),
        "mae_model": round(mae_m, 1), "mae_baseline": round(mae_b, 1),
        "selisih_pct": round((mae_m / mae_b - 1) * 100, 2),
        "mape_model": round(mean_absolute_percentage_error(y, model_pred) * 100, 3),
        "mape_baseline": round(mean_absolute_percentage_error(y, baseline_pred) * 100, 3),
        "model_menang": bool(mae_m < mae_b),
        "lam": lam, "gate": gate,
    })


def jalankan_direct(df, fitur, fitur_target, varian, rows):
    akhir = df["tanggal"].max()
    kol = fitur + fitur_target
    for h in HORIZON_DIRECT:
        d = bangun_direct(df, h, varian)
        for fold, mulai, selesai, mask_test in folds(d, "tanggal_target", akhir):
            train = d[d["tanggal_target"] <= mulai - pd.Timedelta(days=h)]
            test = d[mask_test]
            if len(test) == 0 or len(train) < 1000:
                continue
            if varian == "l2":
                bundle = latih_l2(train, kol, "harga_target", "harga")
                val_cut = train["tanggal_target"].max() - pd.Timedelta(days=60)
                val = train[train["tanggal_target"] > val_cut]
                lam, gate = pilih_l2(bundle, val, kol, "harga_target", "harga")
                delta = terapkan_l2(bundle, test, kol, "harga", lam, gate)
            else:
                m = latih(train[kol], train["harga_target"] - train["harga"])
                delta = m.predict(test[kol])
            pred = test["harga"].to_numpy() + delta
            evaluasi(rows, "direct", varian, h, fold, mulai, selesai,
                     test["harga_target"], pred, test["harga"],
                     lam if varian == "l2" else None,
                     gate if varian == "l2" else None)


def jalankan_recursive(df, fitur, varian, rows):
    akhir = df["tanggal"].max()
    d = df.reset_index(drop=True)
    if varian != "baseline":
        d = _kalender_l1(d, "tanggal", "")
    d["delta"] = d["harga"] - d["harga_lag1"]
    g = d.groupby(["pasar", "komoditas"], observed=True)
    d["baseline_h2"] = g["harga"].shift(2)
    d["baseline_h3"] = g["harga"].shift(3)
    for fold, mulai, selesai, mask_test in folds(d, "tanggal", akhir):
        train = d[(d["tanggal"] <= mulai - pd.Timedelta(days=3))
                  & d["harga_lag1"].notna() & d["harga"].notna()]
        if varian == "l2":
            bundle = latih_l2(train, fitur, "harga", "harga_lag1")
            val_cut = train["tanggal"].max() - pd.Timedelta(days=60)
            val = train[train["tanggal"] > val_cut]
            lam, gate = pilih_l2(bundle, val, fitur, "harga", "harga_lag1")
            d["pred_h1"] = d["harga_lag1"] + terapkan_l2(bundle, d, fitur, "harga", lam, gate)
            reg = bundle["reg"]
        else:
            m = latih(train[fitur], train["delta"])
            d["pred_h1"] = d["harga_lag1"] + m.predict(d[fitur])
            reg, lam = m, 1.0
        d["lag1_h2"] = d.groupby(["pasar", "komoditas"], observed=True)["pred_h1"].shift(1)
        X2 = d[fitur].copy(); X2["harga_lag1"] = d["lag1_h2"]
        d["pred_h2"] = d["lag1_h2"] + lam * reg.predict(X2)
        d["lag1_h3"] = d.groupby(["pasar", "komoditas"], observed=True)["pred_h2"].shift(1)
        X3 = d[fitur].copy(); X3["harga_lag1"] = d["lag1_h3"]
        d["pred_h3"] = d["lag1_h3"] + lam * reg.predict(X3)
        for h, pred_kol, base_kol in [(1, "pred_h1", "harga_lag1"),
                                      (2, "pred_h2", "baseline_h2"),
                                      (3, "pred_h3", "baseline_h3")]:
            test = d[mask_test]
            mask = test["harga"].notna() & test[pred_kol].notna() & test[base_kol].notna()
            evaluasi(rows, "recursive", varian, h, fold, mulai, selesai,
                     test.loc[mask, "harga"], test.loc[mask, pred_kol],
                     test.loc[mask, base_kol],
                     lam if varian == "l2" else None,
                     gate if varian == "l2" else None)


def ringkas(df):
    print("\n=== Agregat per jalur/horizon (4 fold) ===")
    agg = (df.groupby(["jalur", "horizon"])
             .apply(lambda x: pd.Series({
                 "fold_menang": int(x["model_menang"].sum()),
                 "mae_model": round(x["mae_model"].mean(), 0),
                 "mae_baseline": round(x["mae_baseline"].mean(), 0),
                 "selisih_pct_rata2": round(x["selisih_pct"].mean(), 2),
                 "selisih_pct_terbaik": round(x["selisih_pct"].min(), 2),
                 "mape_model": round(x["mape_model"].mean(), 2),
                 "mape_baseline": round(x["mape_baseline"].mean(), 2),
             }), include_groups=False))
    print(agg.to_string())
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--varian", default="baseline", choices=["baseline", "l1", "l2"])
    ap.add_argument("--out", default=str(MODELS / "hasil_evaluasi_walkforward.csv"))
    args = ap.parse_args()

    df, fitur, fitur_target = muat_data(args.varian)
    rows = []
    jalankan_direct(df, fitur, fitur_target, args.varian, rows)
    jalankan_recursive(df, fitur, args.varian, rows)
    hasil = pd.DataFrame(rows)
    hasil.to_csv(args.out, index=False)
    print(f"Disimpan ke {args.out} ({len(hasil)} baris)")
    ringkas(hasil)


if __name__ == "__main__":
    sys.exit(main())
