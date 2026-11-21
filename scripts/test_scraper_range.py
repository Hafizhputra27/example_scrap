#!/usr/bin/env python3
"""Self-check untuk scraper inkremental (tanpa pytest, tanpa jaringan).

    python3 scripts/test_scraper_range.py

Yang dijaga:
- `parse_table` tetap jalan untuk hari yang belum terbit (semua harga kosong)
  dan tidak melempar error.
- `scrape_range` melewati hari dengan 0 harga (tidak menulis baris NaN) dan
  melempar ValueError kalau seluruh rentang kosong.
- `rentang_scrape` memilih "hari setelah data terakhir s/d kemarin", dengan
  override argv.
- `refresh_harga` berhenti non-zero kalau frame baru 0 harga terisi.
- `_sampai` tidak pernah meminta tanggal hari ini atau ke depan.
"""

import contextlib
import io
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scraper_sibapokting as scraper  # noqa: E402
import refresh_sumber_data as refresh  # noqa: E402


def html_tabel(rows: list[tuple[str, str]]) -> str:
    """HTML tabel bergaya SIBAPOKTING: satu kolom per pasar + Jumlah Pasar/Rata-Rata."""
    body = "".join(
        f"<tr><td>{kom}</td><td>{harga}</td><td>1</td><td>{harga}</td></tr>"
        for kom, harga in rows
    )
    return (
        "<table><thead><tr><th>Nama Komoditas</th><th>Pasar Margahayu</th>"
        "<th>Jumlah Pasar</th><th>Rata-Rata</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def test_parse_table_kosong() -> None:
    df = scraper.parse_table(
        html_tabel([("CABE RAWIT MERAH", "-"), ("BAWANG MERAH", "")]), "2026-11-21"
    )
    assert list(df.columns) == ["tanggal", "pasar", "komoditas", "harga"], df.columns
    assert len(df) == 2, df
    assert df["harga"].isna().all(), df
    assert df["pasar"].unique().tolist() == ["Pasar Margahayu"], df


def test_rentang_scrape() -> None:
    hari_ini = date(2026, 11, 21)

    # Belum ada data mentah: mulai dari awal cakupan proyek, s/d kemarin.
    assert scraper.rentang_scrape(None, hari_ini) == (date(2024, 8, 22), date(2026, 11, 20))

    # Data terakhir 19 Nov: minta hanya 20 Nov (bukan rentang hardcode 2024-2026).
    assert scraper.rentang_scrape(date(2026, 11, 19), hari_ini) == (
        date(2026, 11, 20),
        date(2026, 11, 20),
    )

    # Override argv menimpa batas akhir.
    assert scraper.rentang_scrape(date(2026, 11, 19), hari_ini, "2026-11-25") == (
        date(2026, 11, 20),
        date(2026, 11, 25),
    )

    # Override yang lebih tua dari data terakhir = tidak ada yang baru.
    mulai, sampai = scraper.rentang_scrape(date(2026, 11, 19), hari_ini, "2026-11-18")
    assert mulai > sampai, (mulai, sampai)

    # Tanggal terakhir dibaca dari CSV mentah.
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "harga_sibapokting.csv"
        raw.write_text("tanggal,pasar,komoditas,harga\n2026-11-18,P1,TOMAT,1000\n2026-11-19,P1,TOMAT,2000\n")
        assert scraper.terakhir_di_raw(raw) == date(2026, 11, 19)
        raw.unlink()
        assert scraper.terakhir_di_raw(raw) is None


def test_scrape_range_lewati_belum_terbit() -> None:
    scraper.get_initial_state = lambda: ("csrf", "snapshot")

    def fake_fetch(_csrf, _snapshot, tanggal_str):
        if tanggal_str == "2026-11-21":
            return html_tabel([("CABE RAWIT MERAH", "-"), ("BAWANG MERAH", "-")])
        return html_tabel([("CABE RAWIT MERAH", "Rp. 60.000"), ("BAWANG MERAH", "Rp. 35.000")])

    scraper.fetch_harga_by_date = fake_fetch

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "harga.csv"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            df = scraper.scrape_range(
                date(2026, 11, 20), date(2026, 11, 21), delay_seconds=0, output_path=out
            )
        assert set(df["tanggal"]) == {"2026-11-20"}, df["tanggal"].unique()
        assert df["harga"].notna().all(), df
        assert "belum terbit" in buf.getvalue(), buf.getvalue()
        tertulis = pd.read_csv(out)
        assert tertulis["tanggal"].unique().tolist() == ["2026-11-20"], tertulis
        assert tertulis["harga"].notna().all(), tertulis

    # Seluruh rentang belum terbit -> ValueError, bukan CSV berisi NaN.
    scraper.fetch_harga_by_date = lambda *_: html_tabel([("CABE RAWIT MERAH", "-")])
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "harga.csv"
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                scraper.scrape_range(date(2026, 11, 21), date(2026, 11, 21), delay_seconds=0, output_path=out)
        except ValueError:
            pass
        else:
            raise AssertionError("scrape_range harus ValueError kalau semua hari belum terbit")


def test_refresh_harga_tolak_frame_kosong() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "harga_sibapokting.csv"
        raw.write_text("tanggal,pasar,komoditas,harga\n2026-11-19,P1,TOMAT,2000\n")
        refresh.RAW_HARGA = raw

        def fake_scrape(_mulai, _sampai, output_path):
            pd.DataFrame(
                {"tanggal": ["2026-11-20"], "pasar": ["P1"], "komoditas": ["TOMAT"], "harga": [None]}
            ).to_csv(output_path, index=False)
            return pd.DataFrame()

        refresh.scraper.scrape_range = fake_scrape
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                refresh.refresh_harga(date(2026, 11, 20))
        except SystemExit as e:
            assert str(e.code).startswith("harga: 0 harga terisi"), e.code
        else:
            raise AssertionError("refresh_harga harus exit non-zero kalau 0 harga terisi")
        assert raw.read_text().count("2026-11-20") == 0, "data mentah tidak boleh berubah"


def test_sampai_tidak_meminta_masa_depan() -> None:
    asli = sys.argv
    try:
        sys.argv = ["refresh_sumber_data.py", "2099-01-01"]
        with contextlib.redirect_stderr(io.StringIO()) as err:
            sampai = refresh._sampai()
        assert sampai == date.today() - timedelta(days=1), sampai
        assert "clamp" in err.getvalue().lower(), err.getvalue()

        sys.argv = ["refresh_sumber_data.py"]
        assert refresh._sampai() == date.today() - timedelta(days=1)
    finally:
        sys.argv = asli


def test_jalankan_manual_menambah_bukan_menimpa() -> None:
    scraper.get_initial_state = lambda: ("csrf", "snapshot")
    scraper.fetch_harga_by_date = lambda _c, _s, tgl: html_tabel(
        [("CABE RAWIT MERAH", "Rp. 60.000" if tgl == "2026-11-20" else "-")]
    )

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "harga_sibapokting.csv"
        raw.write_text(
            "tanggal,pasar,komoditas,harga\n"
            "2026-11-18,Pasar Margahayu,CABE RAWIT MERAH,58000\n"
            "2026-11-19,Pasar Margahayu,CABE RAWIT MERAH,59000\n"
        )
        scraper.RAW_HARGA = raw
        with contextlib.redirect_stdout(io.StringIO()):
            df = scraper.jalankan_manual(hari_ini=date(2026, 11, 21))

        assert df is not None, "harus ada tanggal baru (2026-11-20)"
        tertulis = pd.read_csv(raw)
        assert tertulis["tanggal"].unique().tolist() == [
            "2026-11-18",
            "2026-11-19",
            "2026-11-20",
        ], tertulis["tanggal"].unique().tolist()
        assert tertulis["harga"].notna().all(), tertulis
        assert not (Path(tmp) / "_harga_scrape_manual.csv").exists()


def main() -> None:
    test_parse_table_kosong()
    test_rentang_scrape()
    test_scrape_range_lewati_belum_terbit()
    test_jalankan_manual_menambah_bukan_menimpa()
    test_refresh_harga_tolak_frame_kosong()
    test_sampai_tidak_meminta_masa_depan()
    print("self-check OK")


if __name__ == "__main__":
    main()
