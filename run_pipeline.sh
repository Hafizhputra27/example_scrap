#!/usr/bin/env bash
# Jalankan seluruh pipeline dari data mentah sampai JSON dashboard.
# Pakai setelah data harga/cuaca/kurs diperbarui.
#   ./run_pipeline.sh          # pipeline penuh + audit
#   ./run_pipeline.sh --cepat  # lewati training ulang model (pakai model tersimpan)
set -euo pipefail
cd "$(dirname "$0")"
PY=python3

echo ">> 1. Bersihkan & gabung data"
$PY scripts/clean_data.py
$PY scripts/combine_data.py
$PY scripts/feature_engineering.py

if [[ "${1:-}" != "--cepat" ]]; then
  echo ">> 2. Latih model"
  $PY scripts/train_model_h1.py
  for H in 1 3 7; do
    $PY scripts/build_dataset_horizon.py $H
    $PY scripts/train_model_horizon.py $H
  done
  $PY scripts/train_klasifikasi_arah.py
  $PY scripts/train_cabai_only.py
else
  echo ">> 2. (dilewati, pakai model tersimpan) -- tetap regenerate dataset horizon"
  for H in 1 3 7; do $PY scripts/build_dataset_horizon.py $H; done
fi

echo ">> 3. Evaluasi & rekomendasi"
$PY scripts/evaluate_multi_horizon.py
$PY scripts/rekomendasi_band_h7.py
$PY scripts/cek_robustness_lebaran.py

echo ">> 4. Prediksi forward & export JSON dashboard"
$PY scripts/predict_forward.py
$PY scripts/export_dashboard.py

echo ">> 5. Audit"
$PY scripts/audit_model.py

echo ">> SELESAI. JSON dashboard ada di dashboard_data/"
