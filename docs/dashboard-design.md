# Design — Dashboard Harga Hasil Bumi (tema hijau)

Pendamping `dashboard-PRD.md`. Semua nilai di sini final kecuali ditandai.

---

## 0. Arah desain

Bukan dashboard "AI kami memprediksi harga!" — temuan sebenarnya adalah *model tidak
mengalahkan tebakan naif, dan yang bergerak itu ketidakpastiannya, bukan titik
tengahnya*. Desain membawa kejujuran intelektual itu: **data-forward, tenang,
sedikit editorial-akademis**, bukan flashy.

Hijau di sini = **daun singkong / pandan** (dalam, sedikit earthy), bukan mint /
emerald SaaS. Warna chart TIDAK hijau semua — hijau adalah warna UI/brand; seri
chart pakai palet colorblind-safe terpisah (§3).

**Signature:** *Pita Ketidakpastian* (§5). **Risiko estetika:** garis chart
bertekstur "tulis tangan" (§6) — menghormati bahwa data ini dicatat manual oleh
petugas pasar, bukan sensor.

## 1. Token warna

### Light (default)

| Token | Hex | Pakai |
|---|---|---|
| `--bg` | `#F4F7EF` | latar halaman (kertas hangat, semburat hijau) |
| `--surface` | `#FFFFFF` | kartu, panel chart |
| `--surface-2` | `#EDF1E6` | inset, baris tabel selang-seling |
| `--ink` | `#1A241A` | teks utama, garis "aktual" di chart |
| `--ink-muted` | `#57634F` | caption, sumbu, garis "baseline" |
| `--line` | `#D7DFC9` | border rambut, grid |
| `--brand` | `#2C6E49` | nav, link, eyebrow, tombol primer, garis kurs |
| `--brand-deep` | `#1C4A31` | hover/active, judul gelap |
| `--signature` | `#8AB84F` | HANYA: garis median pita ketidakpastian + 1 detail hero |

### Dark (`prefers-color-scheme: dark` + toggle)

| Token | Hex |
|---|---|
| `--bg` | `#10140D` |
| `--surface` | `#181E13` |
| `--surface-2` | `#212A1B` |
| `--ink` | `#E9EEE0` |
| `--ink-muted` | `#9AA88C` |
| `--line` | `#2E3826` |
| `--brand` | `#69B487` |
| `--brand-deep` | `#8FCBA5` |
| `--signature` | `#A6D26A` |

Aturan tema: definisikan SEMUA token di `:root` polos (light). Redefinisi hanya token
di bawah `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }`
dan `:root[data-theme="dark"]`. `body { background: var(--bg) }` eksplisit.

## 2. Tipografi

Google Fonts (diizinkan CSP). Selalu sertakan fallback stack.

| Peran | Font | Fallback | Pakai |
|---|---|---|---|
| Display | **Fraunces** 400/600, `opsz` auto | `Georgia, 'Times New Roman', serif` | h1/h2, tesis hero |
| Body/UI | **IBM Plex Sans** 400/500/600 | `system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif` | teks, tombol, label |
| Data/mono | **IBM Plex Mono** 400/500 | `'SF Mono', 'Roboto Mono', ui-monospace, monospace` | angka Rupiah, tick sumbu, timestamp, label "+X% MAE", eyebrow |

```
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
```

Skala:

| Elemen | Spec |
|---|---|
| tesis hero | Fraunces 600 · `clamp(1.75rem, 4vw, 2.75rem)` · lh 1.15 |
| h2 section | Fraunces 600 · `1.5rem` · lh 1.2 |
| eyebrow (kicker) | IBM Plex Mono 500 · `0.75rem` · `letter-spacing .12em` · UPPERCASE · `--brand` |
| h3 | IBM Plex Sans 600 · `1.05rem` |
| body | IBM Plex Sans 400 · `0.95rem` · lh 1.6 |
| caption / tick | IBM Plex Mono 400 · `0.75rem` · `--ink-muted` |
| angka Rupiah | IBM Plex Mono 500 · `font-variant-numeric: tabular-nums` |

## 3. Palet chart (colorblind-safe — SUDAH divalidasi)

Divalidasi dengan `dataviz/scripts/validate_palette.js` (lolos light & dark, urut tetap).

### Kategorikal — urutan entitas→warna TETAP (jangan diputar)

| Slot | Light | Dark | Entitas default |
|---|---|---|---|
| 1 | `#0072B2` biru | `#3C97D4` | pasar spotlight / kondisi "normal" alt |
| 2 | `#009E73` hijau-toska | `#12A97F` | fill pita "normal" |
| 3 | `#E69F00` amber | `#B27B27` | seri "model", fill pita "dekat Lebaran" |

Slot 3 (amber) kontras < 3:1 di light → WAJIB label langsung + tabel-view (sudah
diwajibkan PRD). Seri ke-4+ → lipat jadi "lainnya" / small multiples, jangan tambah hue.

### Chart prediksi (khusus)

| Seri | Warna | Mark |
|---|---|---|
| `aktual` | `--ink` | garis 2.5px (kebenaran, paling menonjol) |
| `model` | amber (slot 3) | garis 2px |
| `baseline` | `--ink-muted` | garis 2px **putus-putus** (4 2) |

### Pita ketidakpastian (p10–p90)

| Kondisi | Fill | Median | Tekstur |
|---|---|---|---|
| normal | hijau-toska (slot 2) @ 14% | garis solid slot 2, 1.5px | — |
| dekat Lebaran | amber (slot 3) @ 14% | garis solid slot 3, 1.5px | hatch 45° hairline (CVD/print) |

### Arah harga (naik/turun/stabil) — diverging, semantik domain

Naik = baik untuk petani yang menjual → hijau di atas.

| Nilai | Light | Dark | Selalu + ikon + label |
|---|---|---|---|
| naik | `#2C7A4B` | `#69B487` | ▲ |
| turun | `#B5502F` (clay) | `#D9805E` | ▼ |
| stabil | `#7B8470` | `#8C9580` | ● |

### Cuaca & kurs

| Chart | Warna |
|---|---|
| curah hujan (bar) | `#3C7A9E` light / `#5FA0C4` dark — satu hue |
| suhu (line + pita min–max) | `#C46A3C` light / `#D98C5E` dark |
| kurs (line, 1 seri) | `--brand` |

## 4. Layout

Satu halaman scroll. Konten `max-width: 1100px`, tengah, padding samping
`clamp(1rem, 5vw, 3rem)`.

```
┌───────────────────────────────────────────────────────────────┐
│ ● Harga Hasil Bumi · Kab. Bandung   Eksplorasi Cuaca Prediksi Band Riset   ☀/☾ │ header sticky, tinggi 56px, border-bottom --line
├───────────────────────────────────────────────────────────────┤
│ Data s/d 22 Agu 2026 · [Cabe Merah Keriting ▾] [rentang 9 pasar ▾] [2 thn ▾]  │ sub-bar sticky (muncul setelah hero), bg --surface
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  RENTANG, BUKAN TITIK                          ← eyebrow       │
│  Yang bisa diprediksi dari harga sayur bukan   ← Fraunces      │
│  angka pastinya, tapi seberapa lebar                           │
│  kemungkinannya bergerak.                                      │
│                                                               │
│  ╭─────────────────────────────────────────────────────────╮  │
│  │     ░░▓▓▓▓▓▓░░░           pita p10–p90 (melebar dekat     │  │ hero chart ~380px
│  │  ──╱╲────╱╲────╲──        Lebaran) + garis median          │  │
│  ╰─────────────────────────────────────────────────────────╯  │
│   25 komoditas    9 pasar    24 bulan          ← mono, muted   │
│                                                               │
│  ── hairline ────────────────────────────────────────────────  │
│                                                               │
│  EKSPLORASI HARGA                                              │
│  intro 1 kalimat.                                              │
│  [envelope 9 pasar + spotlight]        [stat: terakhir/min/max]│
│  ▸ Lihat sebagai tabel                                         │
│  ...                                                           │
└───────────────────────────────────────────────────────────────┘
```

- **Sub-bar** = ruang kontrol. Selector komoditas/pasar/rentang global (banyak section
  merespons). Selalu terjangkau. Mobile: banner tanggal jadi baris sendiri, selector
  horizontal-scroll.
- Ritme antar-section: `margin-block: clamp(3rem, 8vw, 5rem)` + divider `--line`.
- Chart dalam `<figure>`, caption `<figcaption>` di bawah. Tinggi chart 320–380px.
  Sempit → `<div style="overflow-x:auto">`.
- Kartu (prediksi chip, stat tile): `display:grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px`.
- Radius: `--r: 10px` kartu/panel; chart panel `--r`; tombol `8px`; chip `6px`.
  Border 1px `--line` di semua permukaan terangkat.

## 5. Signature — Pita Ketidakpastian

Band p10–p90 BUKAN fill datar transparan, tapi **pita meruncing**: opasitas sedikit
lebih tinggi di tepi (garis p10 & p90 samar terlihat) daripada tengah → terbaca
sebagai *helai fisik* (kain / daun). **Melebar terlihat menjelang Lebaran** — inti
temuan riset.

Muncul di 3 tempat:
1. **Hero** — 2 tahun, 1 komoditas, pita p10–p90 + median.
2. **Section Band** — normal vs Lebaran berdampingan, pita jadi elemen utama.
3. **Dalam tiap prediksi-chip** — mini-ribbon (sparkline) menunjukkan rentang 7-hari
   khas komoditas itu, di belakang angka model & baseline.

Render: SVG. Fill = `<linearGradient>` vertikal dari `hue@8%` (tengah) → `hue@22%`
(tepi). Median = `--signature` (lime) stroke 1.5px, `stroke-linecap: round`. Pita
Lebaran dapat `<pattern>` hatch 45° 1px `--ink-muted@30%` DI ATAS fill (pembeda
non-hue untuk CVD/cetak).

## 6. Risiko estetika — garis "tulis tangan"

Sumbu, tepi pita, dan garis median digambar dengan **tremor 0.5px tak beraturan**
(SVG `<filter>` `feTurbulence` + `feDisplacementMap`, `baseFrequency ~0.012`,
`scale 1.2`). Garis median lebar bervariasi halus. Menandakan: data ini dicatat
tangan oleh petugas pasar, bukan sensor — dan tak ada di sini yang presisi-mesin.

Fallback WAJIB:
- `@media (prefers-reduced-motion: reduce)` → filter mati, garis bersih.
- `@media (prefers-reduced-transparency: reduce)` → fill pita jadi solid 20%, no gradient.
- `@media (forced-colors: active)` → semua filter mati, pakai `CanvasText`/`Canvas`.

Semua elemen lain: disiplin, bersih, tanpa dekorasi.

## 7. Motion

| Momen | Spec | Gated |
|---|---|---|
| Load hero | pita menggambar kiri→kanan 600ms ease-out; stat count-up 800ms | reduced-motion → tampil langsung |
| Section masuk viewport | rise 8px + fade 300ms, stagger 60ms antar-anak | reduced-motion → tampil langsung |
| Hover chart | crosshair snap instan; tooltip fade 100ms | — |
| Toggle tema | transition `background-color`/`color` 200ms | reduced-motion → instan |

Tidak ada: parallax, auto-carousel, animasi loop, angka berkedip.

## 8. Komponen

| Komponen | Spec ringkas |
|---|---|
| **Header** | sticky, `--surface` blur opsional, judul (Fraunces 600 1rem) + titik `--brand` 8px, nav anchor (mono 0.8rem, `--ink-muted`, aktif → `--brand` + underline), toggle tema (ikon ☀/☾, 40px hit) |
| **Sub-bar kontrol** | sticky di bawah header, `--surface`, border-bottom. Banner tanggal (mono, `--ink-muted`) + 3 `<select>` bergaya (border `--line`, radius 8px, chevron custom) |
| **Section** | `<section id>` : eyebrow → h2 → `<p>` intro (`--ink-muted`, max 60ch) → konten |
| **Figure chart** | `<figure>` : panel `--surface` border `--line` radius `--r` padding 16px → `<svg>` → di luar panel: `<figcaption>` (mono 0.75rem) + `<details>` "Lihat sebagai tabel" |
| **prediksi-chip** | kartu: header komoditas@pasar → baris `model` (amber dot + angka mono besar) → baris `baseline` (muted dot + angka) → footer label `model +X% MAE` (mono, `--ink-muted`) → mini-ribbon di background. Kalau sel kosong: `data tidak tersedia` + alasan. |
| **stat tile** | angka besar (Fraunces 600) + label (mono uppercase 0.7rem `--ink-muted`). TIDAK pakai warna seri. |
| **badge caveat** | pill kecil, `--surface-2`, border `--line`, ikon ⚠, teks "data 1–3 pasar jarang lapor" |
| **tabel-view** | `<table>` dalam `<details>`; header `--surface-2`, angka `tabular-nums` rata kanan, baris selang-seling `--surface-2` |
| **banner kejujuran** | di section Prediksi: bar `--surface-2` border-left 3px `--brand`, teks: "Prediksi dihitung dari data terakhir <tanggal>. Model ML secara historis kurang akurat dari baseline — ditampilkan sebagai pembanding." |

## 9. Spesifikasi chart (dari skill dataviz)

- **Marks:** garis 2px; ujung data bar radius 4px menempel baseline; marker ≥ 8px;
  gap permukaan 2px antar-fill; grid & sumbu recessive (`--line`, 1px).
- **Legend:** selalu ada untuk ≥ 2 seri (1 seri → judul saja). ≤ 4 seri juga
  diberi label langsung. Teks legend/label pakai token teks, BUKAN warna seri.
- **Hover:** default menyala. Line/area → crosshair + tooltip. Bar/dot → tooltip per-mark.
  Hit target > mark. Filter satu baris di atas chart (= sub-bar global).
- **Satu sumbu.** Curah hujan & suhu = DUA chart terpisah, jangan dual-axis.
- **Tabel:** setiap chart punya `<details>` tabel.
- **Dark mode:** langkah warna dark sudah divalidasi (§3), bukan flip otomatis.

Per chart:

| Chart | Form | Catatan |
|---|---|---|
| Hero ribbon | line + band | 2 thn, median + pita p10–p90, penanda vertikal di 2 tanggal Lebaran |
| Eksplorasi harga | line + envelope | default: area min–max 9 pasar (`--line` fill) + garis rata-rata (`--ink`); spotlight 1 pasar → garis biru (slot 1) 2.5px, envelope jadi abu |
| Curah hujan | bar harian | 1 hue, baseline 0, radius 4px ujung |
| Suhu | line + pita | avg (garis) + min–max (pita 12%) |
| Kurs | line | 1 seri `--brand`, no legend |
| Backtest prediksi | 3 line | aktual/model/baseline (§3), 60 hari, MAE sebagai teks di caption |
| MAE per horizon | grouped bar | model (amber) vs baseline (muted), label `+X%` di atas bar model |
| Band per komoditas | dot + range | 25 baris (komoditas di y), titik median + garis p10–p90, normal vs Lebaran (2 warna, offset vertikal) |
| Kalkulator band | band tunggal + penanda | input harga → pita nilai absolut + penanda p10/median/p90 |

## 10. Aksesibilitas — lantai kualitas

- Fokus keyboard terlihat: `:focus-visible` outline 2px `--brand` offset 2px.
- Kontras teks: `--ink` / `--bg` ≥ 7:1; `--ink-muted` / `--bg` ≥ 4.5:1 (verifikasi saat implementasi).
- Semua chart: `role="img"` + `aria-label` ringkas + `<details>` tabel.
- Identitas seri tak pernah warna-saja (legend + label + untuk arah: ikon).
- `prefers-reduced-motion`, `prefers-reduced-transparency`, `forced-colors` dihormati (§6).
- Target sentuh ≥ 40px. Body tidak pernah scroll horizontal.
- `<html lang="id">`.

## 11. Starter `:root` (CSS)

```css
:root {
  --bg:#F4F7EF; --surface:#FFFFFF; --surface-2:#EDF1E6;
  --ink:#1A241A; --ink-muted:#57634F; --line:#D7DFC9;
  --brand:#2C6E49; --brand-deep:#1C4A31; --signature:#8AB84F;
  --cat-1:#0072B2; --cat-2:#009E73; --cat-3:#E69F00;
  --naik:#2C7A4B; --turun:#B5502F; --stabil:#7B8470;
  --rain:#3C7A9E; --temp:#C46A3C;
  --r:10px;
  --font-display:'Fraunces',Georgia,'Times New Roman',serif;
  --font-body:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  --font-mono:'IBM Plex Mono','SF Mono','Roboto Mono',ui-monospace,monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:#10140D; --surface:#181E13; --surface-2:#212A1B;
    --ink:#E9EEE0; --ink-muted:#9AA88C; --line:#2E3826;
    --brand:#69B487; --brand-deep:#8FCBA5; --signature:#A6D26A;
    --cat-1:#3C97D4; --cat-2:#12A97F; --cat-3:#B27B27;
    --naik:#69B487; --turun:#D9805E; --stabil:#8C9580;
    --rain:#5FA0C4; --temp:#D98C5E;
  }
}
:root[data-theme="dark"] {
  --bg:#10140D; --surface:#181E13; --surface-2:#212A1B;
  --ink:#E9EEE0; --ink-muted:#9AA88C; --line:#2E3826;
  --brand:#69B487; --brand-deep:#8FCBA5; --signature:#A6D26A;
  --cat-1:#3C97D4; --cat-2:#12A97F; --cat-3:#B27B27;
  --naik:#69B487; --turun:#D9805E; --stabil:#8C9580;
  --rain:#5FA0C4; --temp:#D98C5E;
}
body { background: var(--bg); color: var(--ink); font-family: var(--font-body); }
```
