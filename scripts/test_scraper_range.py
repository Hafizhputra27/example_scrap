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
- Request awal scraper: 5xx/526 diulang lalu lanjut, 4xx tidak diulang, dan
  5xx terus = gagal keras dengan URL + status di pesan.
"""

import contextlib
import io
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

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
    # Default arg `terakhir_di_raw(path=RAW_HARGA)` diikat saat import, jadi patch
    # fungsi ini langsung; kalau tidak, test bergantung umur data di repo.
    scraper.terakhir_di_raw = lambda _path=None: date(2026, 11, 19)
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


HALAMAN_AWAL = (
    '<meta name="csrf-token" content="tok-uji">'
    '<div wire:snapshot="snap-uji"></div>'
)


class RespPalsu:
    def __init__(self, status_code: int, text: str = "", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class SesiPalsu:
    """Ganti `scraper.session`: kembalikan respons berurutan, catat panggilan."""

    def __init__(self, respons: list):
        self.respons = list(respons)
        self.panggilan: list[tuple[str, str]] = []

    def request(self, method: str, url: str, **_kwargs):
        self.panggilan.append((method, url))
        item = self.respons.pop(0) if len(self.respons) > 1 else self.respons[0]
        if isinstance(item, Exception):
            raise item
        return item


@contextlib.contextmanager
def tanpa_tidur():
    asli = scraper.time.sleep
    scraper.time.sleep = lambda _detik: None
    try:
        yield
    finally:
        scraper.time.sleep = asli


def test_retry_526_lalu_200() -> None:
    sesi = SesiPalsu([RespPalsu(526), RespPalsu(200, HALAMAN_AWAL)])
    asli_sesi, asli_percobaan = scraper.session, scraper.PERCOBAAN_MAKS
    scraper.session = sesi
    try:
        with tanpa_tidur(), contextlib.redirect_stderr(io.StringIO()) as err:
            assert scraper.get_initial_state() == ("tok-uji", "snap-uji")
    finally:
        scraper.session, scraper.PERCOBAAN_MAKS = asli_sesi, asli_percobaan

    assert len(sesi.panggilan) == 2, sesi.panggilan
    assert "526" in err.getvalue() and "/harian" in err.getvalue(), err.getvalue()

    # POST livewire ikut diulang, bukan cuma GET halaman awal.
    sesi = SesiPalsu([
        RespPalsu(503),
        RespPalsu(200, payload={"components": [{"effects": {"html": "<table></table>"}}]}),
    ])
    scraper.session = sesi
    try:
        with tanpa_tidur(), contextlib.redirect_stderr(io.StringIO()):
            assert scraper.fetch_harga_by_date("tok", "snap", "2026-11-23") == "<table></table>"
    finally:
        scraper.session = asli_sesi
    assert [p[0] for p in sesi.panggilan] == ["POST", "POST"], sesi.panggilan


def test_4xx_tidak_diulang() -> None:
    sesi = SesiPalsu([RespPalsu(404)])
    asli_sesi = scraper.session
    scraper.session = sesi
    try:
        with tanpa_tidur(), contextlib.redirect_stderr(io.StringIO()):
            scraper.get_initial_state()
    except requests.HTTPError:
        pass
    else:
        raise AssertionError("404 harus melempar HTTPError")
    finally:
        scraper.session = asli_sesi
    assert len(sesi.panggilan) == 1, f"4xx tidak boleh diulang: {sesi.panggilan}"


def test_retry_526_terus_gagal_keras() -> None:
    sesi = SesiPalsu([RespPalsu(526)])
    asli_sesi = scraper.session
    scraper.session = sesi
    try:
        with tanpa_tidur(), contextlib.redirect_stderr(io.StringIO()):
            scraper.get_initial_state()
    except RuntimeError as e:
        pesan = str(e)
    else:
        raise AssertionError("526 terus harus RuntimeError, bukan lanjut")
    finally:
        scraper.session = asli_sesi
    assert "/harian" in pesan and "526" in pesan, pesan
    assert len(sesi.panggilan) == scraper.PERCOBAAN_MAKS, sesi.panggilan

    # Proses harus keluar non-zero dengan pesan yang sama (bukan traceback tanpa konteks).
    kode = (
        "import sys\n"
        "sys.path.insert(0, '.')\n"
        "import scraper_sibapokting as s\n"
        "class R:\n"
        "    status_code = 526\n"
        "    text = ''\n"
        "    def raise_for_status(self): pass\n"
        "class S:\n"
        "    def request(self, *a, **k): return R()\n"
        "s.session = S()\n"
        "s.time.sleep = lambda _d: None\n"
        "s.get_initial_state()\n"
    )
    hasil = subprocess.run(
        [sys.executable, "-c", kode],
        cwd=Path(__file__).resolve().parent,
        capture_output=True,
        text=True,
    )
    assert hasil.returncode != 0, hasil
    assert "/harian" in hasil.stderr and "526" in hasil.stderr, hasil.stderr


def main() -> None:
    # Retry dites lebih dulu: test lain mengganti `get_initial_state`/`fetch_harga_by_date`
    # dengan lambda dan tidak mengembalikannya.
    test_retry_526_lalu_200()
    test_4xx_tidak_diulang()
    test_retry_526_terus_gagal_keras()
    test_parse_table_kosong()
    test_rentang_scrape()
    test_scrape_range_lewati_belum_terbit()
    test_jalankan_manual_menambah_bukan_menimpa()
    test_refresh_harga_tolak_frame_kosong()
    test_sampai_tidak_meminta_masa_depan()
    print("self-check OK")


if __name__ == "__main__":
    main()
