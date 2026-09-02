# Dashboard Harga Hasil Bumi — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static React dashboard that visualizes 2 years of Kabupaten Bandung vegetable-price data, the ML model's (honest) performance, and empirical price-movement bands — from 8 static JSON files.

**Architecture:** Single-page React app (Vite). No backend. Reads `public/data/*.json` produced by the `example_scrap` pipeline. Global filter state (commodity/market/range/theme) in React Context. Charts via Recharts. Deploys as static `dist/`.

**Tech Stack:** React 18, Vite 5, Recharts 2, Vitest + @testing-library/react + jsdom (dev only). Google Fonts (Fraunces, IBM Plex Sans, IBM Plex Mono).

**Spec:** `docs/dashboard-PRD.md` + `docs/dashboard-design.md` (copy both into the dashboard repo's `docs/`).

## Global Constraints

- **Runtime dependencies: exactly `react`, `react-dom`, `recharts`.** Nothing else ships in the bundle.
- **No backend, no external API calls.** Only `fetch('/data/<file>.json')` (relative).
- **Every model prediction renders paired with its baseline** + a `model +X% MAE` label. Never a lone model number.
- **The data-date banner** (`meta.tanggal_data_terakhir`) is always visible once past the hero.
- **Every chart has:** a `<Legend>` for ≥2 series (none for 1), token-colored text (never series color), a `<TabelView>` alternative inside `<details>`, and `isAnimationActive={!prefersReducedMotion}`.
- **One y-axis per chart.** Curah hujan and suhu are two separate charts.
- **Chart colors come from `tokens.js`** (`src/tokens.js`), never hardcoded in components. Light + dark hex values are fixed in design doc §12.
- **Language: Indonesian.** `<html lang="id">`.
- **3 caveat commodities** (`BAWANG MERAH BATU`, `SAYURAN KENTANG LOKAL`, `KACANG TANAH KUPAS`) and empty market×commodity cells are marked explicitly, never silently hidden.
- Commit after every task. Conventional commit messages.

---

## File Structure

```
dashboard-harga-sayur/
├── index.html                  # <html lang="id">, font <link>, #root
├── package.json
├── vite.config.js              # base path for GitHub Pages; vitest config
├── public/data/*.json          # 8 files copied from example_scrap/dashboard_data/
├── src/
│   ├── main.jsx                # ReactDOM root
│   ├── App.jsx                 # shell: header, sub-bar, nav, 6 <section>
│   ├── styles.css              # design doc §11 :root + global + layout
│   ├── tokens.js               # design doc §12 — getTokens(theme)
│   ├── store/
│   │   ├── dates.js            # offsetToDate, formatTanggal, indexOfDate
│   │   ├── DataContext.jsx     # useData(file) — lazy fetch + cache
│   │   ├── FilterContext.jsx   # useFilter() — komoditas/pasar/rentang
│   │   └── ThemeContext.jsx    # useTheme(), useTokens(), usePrefersReducedMotion()
│   ├── lib/
│   │   ├── series.js           # buildEnvelope, sliceRange, extractSpotlight
│   │   ├── stats.js            # ringkasHarga, maeDeret
│   │   └── rekomendasi.js      # rekomendasiBand() — port of rekomendasi_band_h7.py
│   ├── charts/
│   │   ├── ChartFrame.jsx      # <figure> + panel + <figcaption> + <TabelView>
│   │   ├── tooltip.jsx         # <TooltipKustom> shared
│   │   ├── PitaKetidakpastian.jsx
│   │   ├── HargaChart.jsx
│   │   ├── CurahHujanChart.jsx
│   │   ├── SuhuChart.jsx
│   │   ├── KursChart.jsx
│   │   ├── BacktestChart.jsx
│   │   ├── MaeHorizonChart.jsx
│   │   └── BandKomoditasChart.jsx
│   ├── components/
│   │   ├── Selector.jsx
│   │   ├── ThemeToggle.jsx
│   │   ├── BadgeCaveat.jsx
│   │   ├── BannerKejujuran.jsx
│   │   ├── PrediksiChip.jsx
│   │   ├── TabelView.jsx
│   │   └── StatTile.jsx
│   └── sections/
│       ├── Hero.jsx
│       ├── EksplorasiHarga.jsx
│       ├── CuacaKurs.jsx
│       ├── PrediksiModel.jsx
│       ├── RekomendasiBand.jsx
│       └── RingkasanRiset.jsx
└── docs/                        # PRD + design + this plan
```

---

## Task 1: Scaffold, tokens, global styles

**Files:**
- Create: `package.json`, `vite.config.js`, `index.html`, `src/main.jsx`, `src/App.jsx`, `src/styles.css`, `src/tokens.js`
- Create: `src/tokens.test.js`
- Copy: `example_scrap/dashboard_data/*.json` → `public/data/`

**Interfaces:**
- Produces: `getTokens(theme: 'light'|'dark') → {ink, inkMuted, line, surface, bg, brand, signature, cat1, cat2, cat3, naik, turun, stabil, rain, temp}` (all hex strings)

- [ ] **Step 1: Init project**

```bash
npm create vite@latest dashboard-harga-sayur -- --template react
cd dashboard-harga-sayur
npm install recharts
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
mkdir -p public/data
cp ../example_scrap/dashboard_data/*.json public/data/
```

- [ ] **Step 2: `vite.config.js`**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: process.env.DEPLOY_BASE || '/',   // set to '/dashboard-harga-sayur/' for GitHub Pages
  test: { environment: 'jsdom', setupFiles: './src/test-setup.js', globals: true },
})
```

Create `src/test-setup.js`:
```js
import '@testing-library/jest-dom/vitest'
```

Add to `package.json` scripts: `"test": "vitest run"`, `"test:watch": "vitest"`.

- [ ] **Step 3: `index.html`**

```html
<!doctype html>
<html lang="id">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Harga Hasil Bumi · Kab. Bandung</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 4: `src/tokens.js`** — copy design doc §12 verbatim (LIGHT, DARK, `getTokens`).

- [ ] **Step 5: Write the failing test — `src/tokens.test.js`**

```js
import { getTokens } from './tokens'

test('getTokens returns dark cat3 amber', () => {
  expect(getTokens('dark').cat3).toBe('#B27B27')
})
test('getTokens defaults to light', () => {
  expect(getTokens('light').cat3).toBe('#E69F00')
  expect(getTokens(undefined).bg).toBe('#F4F7EF')
})
```

- [ ] **Step 6: Run — `npm test`** → PASS (tokens.js already written).

- [ ] **Step 7: `src/styles.css`** — copy design doc §11 `:root` block, then add global reset + layout primitives:

```css
* { box-sizing: border-box; }
body { margin: 0; font-family: var(--font-body); font-size: 0.95rem; line-height: 1.6; }
h1,h2 { font-family: var(--font-display); font-weight: 600; }
.eyebrow { font-family: var(--font-mono); font-weight: 500; font-size: .75rem; letter-spacing: .12em; text-transform: uppercase; color: var(--brand); }
.mono { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.wrap { max-width: 1100px; margin: 0 auto; padding-inline: clamp(1rem, 5vw, 3rem); }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r); }
:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; } }
```

- [ ] **Step 8: Minimal `src/main.jsx` + `src/App.jsx`**

```jsx
// main.jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'
ReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)
```
```jsx
// App.jsx
export default function App() {
  return <div className="wrap"><h1>Harga Hasil Bumi · Kab. Bandung</h1></div>
}
```

- [ ] **Step 9: Verify** — `npm run dev`, page loads with heading in Fraunces, no console errors.

- [ ] **Step 10: Commit**

```bash
git init && git add -A
git commit -m "chore: scaffold vite react app + design tokens"
```

---

## Task 2: Date helpers

**Files:**
- Create: `src/store/dates.js`, `src/store/dates.test.js`

**Interfaces:**
- Produces:
  - `offsetToDate(tanggalAwal: string, offset: number) → Date`
  - `formatTanggal(d: Date | string, opts?: {pendek?: boolean}) → string` (e.g. `"22 Agu 2026"` / `"22 Agustus 2026"`)
  - `indexOfDate(tanggalAwal: string, target: string) → number` (day offset, floor)

- [ ] **Step 1: Write the failing test**

```js
import { offsetToDate, formatTanggal, indexOfDate } from './dates'

test('offsetToDate adds days from tanggalAwal', () => {
  expect(offsetToDate('2024-08-22', 0).toISOString().slice(0,10)).toBe('2024-08-22')
  expect(offsetToDate('2024-08-22', 10).toISOString().slice(0,10)).toBe('2024-09-01')
})
test('formatTanggal Indonesian short & long', () => {
  expect(formatTanggal('2026-08-22', { pendek: true })).toBe('22 Agu 2026')
  expect(formatTanggal('2026-03-21')).toBe('21 Maret 2026')
})
test('indexOfDate returns day offset', () => {
  expect(indexOfDate('2024-08-22', '2024-08-22')).toBe(0)
  expect(indexOfDate('2024-08-22', '2026-08-22')).toBe(730)
})
```

- [ ] **Step 2: Run — `npm test src/store/dates.test.js`** → FAIL (module not found).

- [ ] **Step 3: Implement `src/store/dates.js`**

```js
const BULAN_PENDEK = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des']
const BULAN_PANJANG = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember']
const MS_HARI = 86400000

const toDate = (v) => (v instanceof Date ? v : new Date(v + 'T00:00:00Z'))

export function offsetToDate(tanggalAwal, offset) {
  return new Date(toDate(tanggalAwal).getTime() + offset * MS_HARI)
}
export function formatTanggal(d, { pendek = false } = {}) {
  const dt = toDate(d)
  const tbl = pendek ? BULAN_PENDEK : BULAN_PANJANG
  return `${dt.getUTCDate()} ${tbl[dt.getUTCMonth()]} ${dt.getUTCFullYear()}`
}
export function indexOfDate(tanggalAwal, target) {
  return Math.floor((toDate(target) - toDate(tanggalAwal)) / MS_HARI)
}
```

- [ ] **Step 4: Run — `npm test`** → PASS.

- [ ] **Step 5: Commit** — `git commit -am "feat: date helpers (id-ID)"`

---

## Task 3: DataContext (lazy JSON fetch + cache)

**Files:**
- Create: `src/store/DataContext.jsx`, `src/store/DataContext.test.jsx`

**Interfaces:**
- Produces:
  - `<DataProvider>` — wraps app
  - `useData(file: string) → {data, loading, error}` — `file` is bare name e.g. `'harga.json'`; fetches `/data/<file>` once, caches across all consumers, returns cached on re-mount.

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen, waitFor } from '@testing-library/react'
import { DataProvider, useData } from './DataContext'

function Probe({ file }) {
  const { data, loading } = useData(file)
  return <div>{loading ? 'loading' : JSON.stringify(data)}</div>
}

test('fetches once and caches', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ a: 1 }) })
  vi.stubGlobal('fetch', fetchMock)
  const { rerender } = render(<DataProvider><Probe file="x.json" /></DataProvider>)
  await waitFor(() => expect(screen.getByText('{"a":1}')).toBeInTheDocument())
  rerender(<DataProvider><Probe file="x.json" /><Probe file="x.json" /></DataProvider>)
  await waitFor(() => expect(screen.getAllByText('{"a":1}').length).toBe(2))
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/data/x.json'))
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/store/DataContext.jsx`**

```jsx
import { createContext, useContext, useEffect, useRef, useState } from 'react'

const Ctx = createContext(null)
const BASE = import.meta.env.BASE_URL || '/'

export function DataProvider({ children }) {
  const cache = useRef(new Map())        // file -> {data} | Promise
  const [, force] = useState(0)
  const get = (file) => {
    const c = cache.current.get(file)
    if (c && !(c instanceof Promise)) return c
    if (!c) {
      const p = fetch(`${BASE}data/${file}`.replace('//data', '/data'))
        .then((r) => { if (!r.ok) throw new Error(`${file} ${r.status}`); return r.json() })
        .then((data) => { cache.current.set(file, { data }); force((n) => n + 1) })
        .catch((error) => { cache.current.set(file, { error }); force((n) => n + 1) })
      cache.current.set(file, p)
    }
    return null
  }
  return <Ctx.Provider value={get}>{children}</Ctx.Provider>
}

export function useData(file) {
  const get = useContext(Ctx)
  const [, setTick] = useState(0)
  useEffect(() => { setTick((n) => n + 1) }, [file])
  const c = get(file)
  return { data: c?.data ?? null, loading: !c, error: c?.error ?? null }
}
```

- [ ] **Step 4: Run** → PASS.

- [ ] **Step 5: Commit** — `git commit -am "feat: lazy JSON DataContext with cache"`

---

## Task 4: FilterContext + ThemeContext

**Files:**
- Create: `src/store/FilterContext.jsx`, `src/store/ThemeContext.jsx`, `src/store/contexts.test.jsx`

**Interfaces:**
- Produces:
  - `<FilterProvider>`, `useFilter() → {komoditas, pasar, rentang, setKomoditas, setPasar, setRentang}` — defaults `komoditas='CABE MERAH KERITING'`, `pasar='__semua__'`, `rentang='2thn'` (`'3bln'|'1thn'|'2thn'`).
  - `<ThemeProvider>`, `useTheme() → {theme, toggle}` (`'light'|'dark'`, initial from `matchMedia('(prefers-color-scheme: dark)')`, writes `document.documentElement.dataset.theme`), `useTokens() → tokens object` (from `getTokens(theme)`), `usePrefersReducedMotion() → boolean`.

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen, act } from '@testing-library/react'
import { FilterProvider, useFilter } from './FilterContext'
import { ThemeProvider, useTheme, useTokens } from './ThemeContext'

function FProbe() {
  const f = useFilter()
  return <button onClick={() => f.setKomoditas('BAWANG MERAH')}>{f.komoditas}|{f.rentang}</button>
}
test('filter defaults and setter', () => {
  render(<FilterProvider><FProbe /></FilterProvider>)
  const b = screen.getByRole('button')
  expect(b).toHaveTextContent('CABE MERAH KERITING|2thn')
  act(() => b.click())
  expect(b).toHaveTextContent('BAWANG MERAH|2thn')
})

function TProbe() {
  const { theme, toggle } = useTheme(); const t = useTokens()
  return <button onClick={toggle}>{theme}:{t.cat3}</button>
}
test('theme toggle swaps tokens + data-theme attr', () => {
  render(<ThemeProvider><TProbe /></ThemeProvider>)
  const b = screen.getByRole('button')
  const first = b.textContent
  act(() => b.click())
  expect(b.textContent).not.toBe(first)
  expect(['light','dark']).toContain(document.documentElement.dataset.theme)
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/store/FilterContext.jsx`**

```jsx
import { createContext, useContext, useState } from 'react'
const Ctx = createContext(null)
export function FilterProvider({ children }) {
  const [komoditas, setKomoditas] = useState('CABE MERAH KERITING')
  const [pasar, setPasar] = useState('__semua__')
  const [rentang, setRentang] = useState('2thn')
  return <Ctx.Provider value={{ komoditas, pasar, rentang, setKomoditas, setPasar, setRentang }}>{children}</Ctx.Provider>
}
export const useFilter = () => useContext(Ctx)
```

- [ ] **Step 4: Implement `src/store/ThemeContext.jsx`**

```jsx
import { createContext, useContext, useEffect, useState } from 'react'
import { getTokens } from '../tokens'
const Ctx = createContext(null)

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() =>
    typeof matchMedia !== 'undefined' && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  useEffect(() => { document.documentElement.dataset.theme = theme }, [theme])
  const toggle = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  return <Ctx.Provider value={{ theme, toggle }}>{children}</Ctx.Provider>
}
export const useTheme = () => useContext(Ctx)
export const useTokens = () => getTokens(useContext(Ctx).theme)
export function usePrefersReducedMotion() {
  const [r, setR] = useState(false)
  useEffect(() => {
    const mq = matchMedia('(prefers-reduced-motion: reduce)')
    const on = () => setR(mq.matches); on(); mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return r
}
```

- [ ] **Step 5: Run** → PASS.

- [ ] **Step 6: Commit** — `git commit -am "feat: filter + theme contexts"`

---

## Task 5: App shell (header, sub-bar, nav, sections)

**Files:**
- Modify: `src/App.jsx`
- Create: `src/components/ThemeToggle.jsx`, `src/components/Selector.jsx`, `src/App.test.jsx`

**Interfaces:**
- Consumes: `DataProvider`, `FilterProvider`, `ThemeProvider`, `useData('meta.json')`, `useFilter`
- Produces: `<Selector kind="komoditas"|"pasar"|"rentang" />` — reads `meta.json` for options, writes to FilterContext.

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen, waitFor } from '@testing-library/react'
import App from './App'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn((url) => {
    if (String(url).includes('meta.json')) return Promise.resolve({ ok: true, json: () => Promise.resolve({
      tanggal_data_terakhir: '2026-08-22', tanggal_data_awal: '2024-08-22',
      pasar: ['Pasar Banjaran','Pasar Ciwidey'],
      komoditas: [{ nama: 'CABE MERAH KERITING', kategori: 'cabai', caveat_data: false }],
      catatan: ['catatan uji'],
    })})
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
  }))
})

test('shell renders nav, data-date banner, 6 sections', async () => {
  render(<App />)
  await waitFor(() => expect(screen.getByText(/22 Agu 2026/)).toBeInTheDocument())
  for (const id of ['eksplorasi','cuaca','prediksi','band','riset']) {
    expect(document.getElementById(id)).toBeInTheDocument()
  }
  expect(screen.getByRole('link', { name: /Eksplorasi Harga/i })).toHaveAttribute('href', '#eksplorasi')
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/components/ThemeToggle.jsx`**

```jsx
import { useTheme } from '../store/ThemeContext'
export default function ThemeToggle() {
  const { theme, toggle } = useTheme()
  return <button onClick={toggle} aria-label={`Ganti ke tema ${theme === 'dark' ? 'terang' : 'gelap'}`}
    style={{ minWidth: 40, minHeight: 40, background: 'transparent', border: '1px solid var(--line)', borderRadius: 8, color: 'var(--ink)', cursor: 'pointer' }}>
    {theme === 'dark' ? '☾' : '☀'}
  </button>
}
```

- [ ] **Step 4: Implement `src/components/Selector.jsx`**

```jsx
import { useData } from '../store/DataContext'
import { useFilter } from '../store/FilterContext'

const RENTANG = [['3bln','3 bulan'],['1thn','1 tahun'],['2thn','2 tahun']]

export default function Selector({ kind }) {
  const { data: meta } = useData('meta.json')
  const f = useFilter()
  if (!meta) return null
  let opts, value, onChange, label
  if (kind === 'komoditas') {
    opts = meta.komoditas.map((k) => [k.nama, k.nama + (k.caveat_data ? ' ⚠' : '')])
    value = f.komoditas; onChange = f.setKomoditas; label = 'Komoditas'
  } else if (kind === 'pasar') {
    opts = [['__semua__', 'Rentang 9 pasar'], ...meta.pasar.map((p) => [p, p])]
    value = f.pasar; onChange = f.setPasar; label = 'Pasar'
  } else {
    opts = RENTANG; value = f.rentang; onChange = f.setRentang; label = 'Rentang waktu'
  }
  return (
    <label className="mono" style={{ display: 'inline-flex', flexDirection: 'column', fontSize: '.7rem', color: 'var(--ink-muted)' }}>
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}
        style={{ fontFamily: 'var(--font-body)', fontSize: '.9rem', color: 'var(--ink)', background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 8, padding: '6px 8px', marginTop: 2 }}>
        {opts.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
      </select>
    </label>
  )
}
```

- [ ] **Step 5: Implement `src/App.jsx`**

```jsx
import { DataProvider, useData } from './store/DataContext'
import { FilterProvider } from './store/FilterContext'
import { ThemeProvider } from './store/ThemeContext'
import ThemeToggle from './components/ThemeToggle'
import Selector from './components/Selector'
import { formatTanggal } from './store/dates'
import Hero from './sections/Hero'
import EksplorasiHarga from './sections/EksplorasiHarga'
import CuacaKurs from './sections/CuacaKurs'
import PrediksiModel from './sections/PrediksiModel'
import RekomendasiBand from './sections/RekomendasiBand'
import RingkasanRiset from './sections/RingkasanRiset'

const NAV = [['eksplorasi','Eksplorasi Harga'],['cuaca','Cuaca & Kurs'],['prediksi','Prediksi Model'],['band','Rekomendasi'],['riset','Ringkasan Riset']]

function Shell() {
  const { data: meta } = useData('meta.json')
  return (
    <>
      <header style={{ position: 'sticky', top: 0, zIndex: 20, background: 'var(--surface)', borderBottom: '1px solid var(--line)' }}>
        <div className="wrap" style={{ display: 'flex', alignItems: 'center', gap: 16, height: 56 }}>
          <strong style={{ fontFamily: 'var(--font-display)' }}>● Harga Hasil Bumi · Kab. Bandung</strong>
          <nav style={{ display: 'flex', gap: 14, marginLeft: 'auto' }} className="mono">
            {NAV.map(([id, t]) => <a key={id} href={`#${id}`} style={{ color: 'var(--ink-muted)', textDecoration: 'none', fontSize: '.8rem' }}>{t}</a>)}
          </nav>
          <ThemeToggle />
        </div>
      </header>
      <div style={{ position: 'sticky', top: 56, zIndex: 19, background: 'var(--surface)', borderBottom: '1px solid var(--line)' }}>
        <div className="wrap" style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end', padding: '10px 0' }}>
          <span className="mono" style={{ color: 'var(--ink-muted)', fontSize: '.8rem' }}>
            Data s/d {meta ? formatTanggal(meta.tanggal_data_terakhir, { pendek: true }) : '…'}
          </span>
          <Selector kind="komoditas" />
          <Selector kind="pasar" />
          <Selector kind="rentang" />
        </div>
      </div>
      <main className="wrap">
        <Hero />
        <section id="eksplorasi"><EksplorasiHarga /></section>
        <section id="cuaca"><CuacaKurs /></section>
        <section id="prediksi"><PrediksiModel /></section>
        <section id="band"><RekomendasiBand /></section>
        <section id="riset"><RingkasanRiset /></section>
      </main>
      <footer className="wrap mono" style={{ color: 'var(--ink-muted)', fontSize: '.75rem', padding: '3rem 0' }}>
        {meta?.catatan?.map((c, i) => <p key={i}>{c}</p>)}
      </footer>
    </>
  )
}

export default function App() {
  return (
    <ThemeProvider><DataProvider><FilterProvider>
      <Shell />
    </FilterProvider></DataProvider></ThemeProvider>
  )
}
```

- [ ] **Step 6: Create stub sections** — each `src/sections/<Name>.jsx` exports `export default function X(){ return <p>TODO</p> }` so App compiles.

- [ ] **Step 7: Run — `npm test`** → PASS. `npm run dev` → header + sticky sub-bar + 3 selectors + 6 sections.

- [ ] **Step 8: Commit** — `git commit -am "feat: app shell — header, sticky control bar, nav, sections"`

---

## Task 6: ChartFrame + TabelView

**Files:**
- Create: `src/charts/ChartFrame.jsx`, `src/components/TabelView.jsx`, `src/charts/tooltip.jsx`, `src/charts/ChartFrame.test.jsx`

**Interfaces:**
- Produces:
  - `<ChartFrame judul caption tabel={{kolom:[...], baris:[[...]]}}>{children}</ChartFrame>` — renders `<figure>` → `.panel` wrapping children → `<figcaption>` → `<details><summary>Lihat sebagai tabel</summary><TabelView/></details>`.
  - `<TabelView kolom={string[]} baris={(string|number)[][]} />`
  - `<TooltipKustom />` — Recharts custom tooltip (pass as `content={<TooltipKustom />}`), formats numbers with `toLocaleString('id-ID')`.

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen } from '@testing-library/react'
import ChartFrame from './ChartFrame'

test('ChartFrame renders figure, caption, and a table view', () => {
  render(
    <ChartFrame judul="Uji" caption="unit rupiah" tabel={{ kolom: ['Tanggal','Harga'], baris: [['1 Jan', 1000]] }}>
      <div>chart</div>
    </ChartFrame>
  )
  expect(screen.getByRole('figure')).toBeInTheDocument()
  expect(screen.getByText('unit rupiah')).toBeInTheDocument()
  expect(screen.getByText('Lihat sebagai tabel')).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Harga' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: '1.000' })).toBeInTheDocument()  // id-ID formatting
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/components/TabelView.jsx`**

```jsx
const fmt = (v) => (typeof v === 'number' ? v.toLocaleString('id-ID') : v)
export default function TabelView({ kolom, baris }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="mono" style={{ borderCollapse: 'collapse', fontSize: '.8rem', width: '100%' }}>
        <thead><tr>{kolom.map((k) => <th key={k} style={{ textAlign: 'right', padding: '4px 8px', background: 'var(--surface-2)', borderBottom: '1px solid var(--line)' }}>{k}</th>)}</tr></thead>
        <tbody>{baris.map((r, i) => <tr key={i} style={{ background: i % 2 ? 'var(--surface-2)' : 'transparent' }}>
          {r.map((c, j) => <td key={j} style={{ textAlign: 'right', padding: '4px 8px' }}>{fmt(c)}</td>)}
        </tr>)}</tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 4: Implement `src/charts/tooltip.jsx`**

```jsx
export function TooltipKustom({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="mono panel" style={{ padding: '8px 10px', fontSize: '.8rem' }}>
      <div style={{ color: 'var(--ink-muted)' }}>{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: p.color }} />
          <span>{p.name}: {typeof p.value === 'number' ? p.value.toLocaleString('id-ID') : p.value}</span>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 5: Implement `src/charts/ChartFrame.jsx`**

```jsx
import TabelView from '../components/TabelView'
export default function ChartFrame({ judul, caption, tabel, children }) {
  return (
    <figure style={{ margin: '0 0 1.5rem' }}>
      {judul && <figcaption className="mono" style={{ fontSize: '.8rem', color: 'var(--ink-muted)', marginBottom: 6 }}>{judul}</figcaption>}
      <div className="panel" style={{ padding: 16 }}>{children}</div>
      {caption && <figcaption className="mono" style={{ fontSize: '.75rem', color: 'var(--ink-muted)', marginTop: 6 }}>{caption}</figcaption>}
      {tabel && (
        <details style={{ marginTop: 6 }}>
          <summary className="mono" style={{ fontSize: '.75rem', color: 'var(--ink-muted)', cursor: 'pointer' }}>Lihat sebagai tabel</summary>
          <TabelView kolom={tabel.kolom} baris={tabel.baris} />
        </details>
      )}
    </figure>
  )
}
```

- [ ] **Step 6: Run — `npm test`** → PASS.

- [ ] **Step 7: Commit** — `git commit -am "feat: ChartFrame + TabelView + custom tooltip"`

---

## Task 7: KursChart (establish the Recharts pattern)

**Files:**
- Create: `src/charts/KursChart.jsx`, `src/charts/KursChart.test.jsx`

**Interfaces:**
- Consumes: `useData('kurs.json')` → `{tanggal_awal, kurs_usd_idr: number[]}`, `useTokens`, `usePrefersReducedMotion`, `offsetToDate`, `formatTanggal`, `<ChartFrame>`
- Produces: `<KursChart />` — a self-contained section body.

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen, waitFor } from '@testing-library/react'
import KursChart from './KursChart'
import { DataProvider } from '../store/DataContext'
import { ThemeProvider } from '../store/ThemeContext'

const wrap = (ui) => <ThemeProvider><DataProvider>{ui}</DataProvider></ThemeProvider>

test('KursChart renders and its table has the data points', async () => {
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({
    tanggal_awal: '2024-08-22', kurs_usd_idr: [15600, 15650, 15700],
  })})))
  render(wrap(<KursChart />))
  await waitFor(() => expect(screen.getByText(/Kurs USD\/IDR/i)).toBeInTheDocument())
  const summary = screen.getByText('Lihat sebagai tabel'); summary.click()
  expect(await screen.findByRole('cell', { name: '15.700' })).toBeInTheDocument()
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/charts/KursChart.jsx`**

```jsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useData } from '../store/DataContext'
import { useTokens, usePrefersReducedMotion } from '../store/ThemeContext'
import { offsetToDate, formatTanggal } from '../store/dates'
import ChartFrame from './ChartFrame'
import { TooltipKustom } from './tooltip'

export default function KursChart() {
  const { data, loading } = useData('kurs.json')
  const t = useTokens()
  const reduced = usePrefersReducedMotion()
  if (loading || !data) return <p className="mono">Memuat kurs…</p>

  const rows = data.kurs_usd_idr.map((v, i) => ({
    t: formatTanggal(offsetToDate(data.tanggal_awal, i), { pendek: true }),
    kurs: v,
  })).filter((r) => r.kurs != null)

  return (
    <ChartFrame
      judul="Kurs USD/IDR"
      caption="Sumber: Frankfurter API (data ECB), weekend/libur di-forward-fill."
      tabel={{ kolom: ['Tanggal', 'Kurs'], baris: rows.filter((_, i) => i % 14 === 0).map((r) => [r.t, r.kurs]) }}
    >
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
          <CartesianGrid stroke={t.line} vertical={false} />
          <XAxis dataKey="t" tick={{ fill: t.inkMuted, fontFamily: 'var(--font-mono)', fontSize: 11 }} minTickGap={48} />
          <YAxis tick={{ fill: t.inkMuted, fontFamily: 'var(--font-mono)', fontSize: 11 }} width={64}
            tickFormatter={(v) => v.toLocaleString('id-ID')} />
          <Tooltip content={<TooltipKustom />} />
          <Line type="monotone" dataKey="kurs" name="Kurs USD/IDR" stroke={t.brand} strokeWidth={2} dot={false}
            isAnimationActive={!reduced} />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
```

- [ ] **Step 4: Run — `npm test`** → PASS.

- [ ] **Step 5: Verify visually** — temporarily render `<KursChart />` in `CuacaKurs` stub, `npm run dev`, eyeball: green line, mono ticks, tooltip on hover, table opens.

- [ ] **Step 6: Commit** — `git commit -am "feat: KursChart — Recharts pattern baseline"`

---

## Task 8: series + stats helpers

**Files:**
- Create: `src/lib/series.js`, `src/lib/stats.js`, `src/lib/series.test.js`, `src/lib/stats.test.js`

**Interfaces:**
- Produces:
  - `buildEnvelope(perPasar: {[pasar]: (number|null)[]}) → {min, max, avg}[]` (index-aligned; nulls skipped; if all null at an index → `{min:null,max:null,avg:null}`)
  - `sliceRange(arr: any[], tanggalAwal: string, rentang: '3bln'|'1thn'|'2thn') → {arr, offset}` — returns the tail slice + the starting offset it began at
  - `ringkasHarga(vals: (number|null)[]) → {terakhir, min, max, median, kosongPct}`
  - `maeDeret(aktual: number[], prediksi: number[]) → number`

- [ ] **Step 1: Write the failing tests — `src/lib/series.test.js`**

```js
import { buildEnvelope, sliceRange } from './series'

test('buildEnvelope skips nulls, all-null → nulls', () => {
  const env = buildEnvelope({ A: [10, null, 30], B: [20, null, null], C: [null, null, 10] })
  expect(env[0]).toEqual({ min: 10, max: 20, avg: 15 })
  expect(env[1]).toEqual({ min: null, max: null, avg: null })
  expect(env[2]).toEqual({ min: 10, max: 30, avg: 20 })
})
test('sliceRange returns tail + offset', () => {
  const a = Array.from({ length: 731 }, (_, i) => i)
  const { arr, offset } = sliceRange(a, '2024-08-22', '3bln')
  expect(arr.length).toBe(90)
  expect(offset).toBe(641)
  expect(sliceRange(a, '2024-08-22', '2thn').arr.length).toBe(731)
})
```

`src/lib/stats.test.js`:
```js
import { ringkasHarga, maeDeret } from './stats'
test('ringkasHarga', () => {
  const r = ringkasHarga([10, null, 30, 20, null])
  expect(r).toEqual({ terakhir: 20, min: 10, max: 30, median: 20, kosongPct: 40 })
})
test('maeDeret', () => {
  expect(maeDeret([10, 20, 30], [12, 18, 33])).toBeCloseTo(2.333, 2)
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/lib/series.js`**

```js
const HARI = { '3bln': 90, '1thn': 365, '2thn': Infinity }

export function buildEnvelope(perPasar) {
  const pasars = Object.values(perPasar)
  const n = pasars[0]?.length ?? 0
  const out = []
  for (let i = 0; i < n; i++) {
    const vals = pasars.map((p) => p[i]).filter((v) => v != null)
    if (!vals.length) { out.push({ min: null, max: null, avg: null }); continue }
    out.push({ min: Math.min(...vals), max: Math.max(...vals), avg: vals.reduce((a, b) => a + b, 0) / vals.length })
  }
  return out
}

export function sliceRange(arr, tanggalAwal, rentang) {
  const want = HARI[rentang] ?? Infinity
  if (want >= arr.length) return { arr, offset: 0 }
  return { arr: arr.slice(arr.length - want), offset: arr.length - want }
}
```

- [ ] **Step 4: Implement `src/lib/stats.js`**

```js
export function ringkasHarga(vals) {
  const ada = vals.filter((v) => v != null)
  const sorted = [...ada].sort((a, b) => a - b)
  const median = sorted.length % 2
    ? sorted[(sorted.length - 1) / 2]
    : (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
  return {
    terakhir: ada.at(-1) ?? null,
    min: sorted[0] ?? null,
    max: sorted.at(-1) ?? null,
    median: median ?? null,
    kosongPct: Math.round(((vals.length - ada.length) / vals.length) * 100),
  }
}
export function maeDeret(aktual, prediksi) {
  const n = Math.min(aktual.length, prediksi.length)
  let s = 0
  for (let i = 0; i < n; i++) s += Math.abs(aktual[i] - prediksi[i])
  return s / n
}
```

- [ ] **Step 5: Run — `npm test`** → PASS.

- [ ] **Step 6: Commit** — `git commit -am "feat: series + stats helpers"`

---

## Task 9: HargaChart + EksplorasiHarga section

**Files:**
- Create: `src/charts/HargaChart.jsx`, `src/components/BadgeCaveat.jsx`, `src/components/StatTile.jsx`
- Modify: `src/sections/EksplorasiHarga.jsx`
- Create: `src/charts/HargaChart.test.jsx`

**Interfaces:**
- Consumes: `useData('harga.json')`, `useData('meta.json')`, `useFilter`, `buildEnvelope`, `sliceRange`, `ringkasHarga`, `<ChartFrame>`, tokens.
  - `harga.json` shape: `{tanggal_awal, n_hari, komoditas: {[nama]: {[pasar]: (number|null)[]}}}`
- Produces: `<HargaChart />`, `<BadgeCaveat>{alasan}</BadgeCaveat>`, `<StatTile label value />`.

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen, waitFor } from '@testing-library/react'
import { DataProvider } from '../store/DataContext'
import { FilterProvider } from '../store/FilterContext'
import { ThemeProvider } from '../store/ThemeContext'
import EksplorasiHarga from '../sections/EksplorasiHarga'

const META = { komoditas: [{ nama: 'CABE MERAH KERITING', kategori: 'cabai', caveat_data: false }], pasar: ['A','B'] }
const HARGA = { tanggal_awal: '2024-08-22', n_hari: 3, komoditas: { 'CABE MERAH KERITING': { A: [40000, 41000, 42000], B: [38000, null, 40000] } } }

beforeEach(() => vi.stubGlobal('fetch', vi.fn((u) => Promise.resolve({ ok: true, json: () => Promise.resolve(
  String(u).includes('meta') ? META : HARGA) }))))

const wrap = (ui) => <ThemeProvider><DataProvider><FilterProvider>{ui}</FilterProvider></DataProvider></ThemeProvider>

test('shows last price and range stats for default commodity', async () => {
  render(wrap(<EksplorasiHarga />))
  await waitFor(() => expect(screen.getByText(/Eksplorasi Harga/i)).toBeInTheDocument())
  expect(screen.getByText('Rp 42.000')).toBeInTheDocument()   // terakhir = avg of [42000,40000]=41000? -> see impl: use avg envelope
})
```

> Note: the test asserts the *stat tile* value. Implementation computes stats from the **average** envelope series for `__semua__`, or the selected market's series otherwise. Adjust the expected string to match the impl you write in Step 3 (compute by hand from HARGA).

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/components/BadgeCaveat.jsx` + `src/components/StatTile.jsx`**

```jsx
// BadgeCaveat.jsx
export default function BadgeCaveat({ children }) {
  return <span className="mono" style={{ display: 'inline-flex', gap: 4, alignItems: 'center', fontSize: '.7rem', color: 'var(--ink-muted)', background: 'var(--surface-2)', border: '1px solid var(--line)', borderRadius: 999, padding: '2px 8px' }}>⚠ {children}</span>
}
```
```jsx
// StatTile.jsx
export default function StatTile({ label, value }) {
  return (
    <div className="panel" style={{ padding: '12px 14px' }}>
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: '1.3rem' }}>{value}</div>
      <div className="mono" style={{ fontSize: '.7rem', textTransform: 'uppercase', letterSpacing: '.08em', color: 'var(--ink-muted)' }}>{label}</div>
    </div>
  )
}
```

- [ ] **Step 4: Implement `src/charts/HargaChart.jsx`**

```jsx
import { ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useData } from '../store/DataContext'
import { useFilter } from '../store/FilterContext'
import { useTokens, usePrefersReducedMotion } from '../store/ThemeContext'
import { offsetToDate, formatTanggal } from '../store/dates'
import { buildEnvelope, sliceRange } from '../lib/series'
import ChartFrame from './ChartFrame'
import { TooltipKustom } from './tooltip'

export default function HargaChart() {
  const { data } = useData('harga.json')
  const { komoditas, pasar, rentang } = useFilter()
  const t = useTokens(); const reduced = usePrefersReducedMotion()
  if (!data) return <p className="mono">Memuat harga…</p>

  const perPasar = data.komoditas[komoditas] || {}
  const env = buildEnvelope(perPasar)
  const spotlight = pasar !== '__semua__' ? (perPasar[pasar] || []) : null

  const full = env.map((e, i) => ({
    t: formatTanggal(offsetToDate(data.tanggal_awal, i), { pendek: true }),
    lo: e.min, hi: e.max, avg: e.avg,
    spot: spotlight ? spotlight[i] : undefined,
  }))
  const { arr: rows } = sliceRange(full, data.tanggal_awal, rentang)

  return (
    <ChartFrame
      judul={`Harga ${komoditas}`}
      caption={pasar === '__semua__' ? 'Area = rentang 9 pasar, garis = rata-rata.' : `Garis tebal = ${pasar}; area = rentang 9 pasar.`}
      tabel={{ kolom: ['Tanggal', 'Min', 'Rata-rata', 'Max'], baris: rows.filter((_, i) => i % 14 === 0).map((r) => [r.t, r.lo, r.avg && Math.round(r.avg), r.hi]) }}
    >
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
          <CartesianGrid stroke={t.line} vertical={false} />
          <XAxis dataKey="t" tick={{ fill: t.inkMuted, fontSize: 11 }} minTickGap={48} />
          <YAxis tick={{ fill: t.inkMuted, fontSize: 11 }} width={72} tickFormatter={(v) => 'Rp ' + v.toLocaleString('id-ID')} />
          <Tooltip content={<TooltipKustom />} />
          <Legend />
          <Area dataKey="hi" name="rentang 9 pasar" stroke="none" fill={t.line} fillOpacity={0.7} isAnimationActive={!reduced} />
          <Area dataKey="lo" stroke="none" fill="var(--surface)" fillOpacity={1} legendType="none" tooltipType="none" isAnimationActive={!reduced} />
          <Line dataKey="avg" name="rata-rata" stroke={t.ink} strokeWidth={2} dot={false} isAnimationActive={!reduced} />
          {spotlight && <Line dataKey="spot" name={pasar} stroke={t.cat1} strokeWidth={2.5} dot={false} isAnimationActive={!reduced} />}
        </ComposedChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
```

- [ ] **Step 5: Implement `src/sections/EksplorasiHarga.jsx`**

```jsx
import { useData } from '../store/DataContext'
import { useFilter } from '../store/FilterContext'
import { sliceRange } from '../lib/series'
import { buildEnvelope } from '../lib/series'
import { ringkasHarga } from '../lib/stats'
import HargaChart from '../charts/HargaChart'
import StatTile from '../components/StatTile'
import BadgeCaveat from '../components/BadgeCaveat'

const CAVEAT = ['BAWANG MERAH BATU', 'SAYURAN KENTANG LOKAL', 'KACANG TANAH KUPAS']

export default function EksplorasiHarga() {
  const { data: harga } = useData('harga.json')
  const { komoditas, pasar, rentang } = useFilter()
  if (!harga) return <p className="mono">Memuat…</p>
  const perPasar = harga.komoditas[komoditas] || {}
  const serie = pasar === '__semua__'
    ? buildEnvelope(perPasar).map((e) => e.avg)
    : (perPasar[pasar] || [])
  const { arr } = sliceRange(serie, harga.tanggal_awal, rentang)
  const s = ringkasHarga(arr)
  const rp = (v) => (v == null ? '—' : 'Rp ' + Math.round(v).toLocaleString('id-ID'))
  return (
    <>
      <p className="eyebrow">Eksplorasi Harga</p>
      <h2>Harga {komoditas} di 9 pasar</h2>
      <p style={{ color: 'var(--ink-muted)', maxWidth: '60ch' }}>Data harian pasar tradisional (tingkat eceran). Pilih komoditas, pasar, dan rentang di bilah atas.</p>
      {CAVEAT.includes(komoditas) && <p><BadgeCaveat>komoditas ini jarang dilaporkan di 1–3 pasar; sebagian data kosong</BadgeCaveat></p>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 12, margin: '16px 0' }}>
        <StatTile label="Harga terakhir" value={rp(s.terakhir)} />
        <StatTile label="Terendah (periode)" value={rp(s.min)} />
        <StatTile label="Tertinggi (periode)" value={rp(s.max)} />
        <StatTile label="Median (periode)" value={rp(s.median)} />
        <StatTile label="Data kosong" value={s.kosongPct + '%'} />
      </div>
      <HargaChart />
    </>
  )
}
```

- [ ] **Step 6: Run — `npm test`** (fix the expected stat string in the test to match hand-computed value) → PASS.

- [ ] **Step 7: Verify visually** — `npm run dev`, switch commodity & market in the sub-bar, confirm chart + stats update, caveat badge shows for the 3 commodities.

- [ ] **Step 8: Commit** — `git commit -am "feat: EksplorasiHarga section — envelope + spotlight + stats"`

---

## Task 10: PitaKetidakpastian + Hero section

**Files:**
- Create: `src/charts/PitaKetidakpastian.jsx`, `src/charts/PitaKetidakpastian.test.jsx`
- Modify: `src/sections/Hero.jsx`

**Interfaces:**
- Consumes: for the hero — `useData('harga.json')` + `useData('band.json')`; `band.json` shape `{horizon, komoditas: {[nama]: {normal: {p10,p25,median,p75,p90,lebar_band,n}, dekat_lebaran: {...}}}}`.
- Produces: `<PitaKetidakpastian data={{t, p10, median, p90}[]} kondisi="normal"|"lebaran" tinggi={number} lebaranX={string[]} />` — renders the band signature.

> **Hero data note:** `band.json` gives *percentages* per commodity, not a daily series. For the hero ribbon over 2 years, build a daily band by taking the selected commodity's daily average price (from `harga.json`) and applying `±` the normal band percentiles as a static ribbon around a smoothed price line: `p10_abs[i] = avg[i] * (1 + band.normal.p10/100)`, etc. This is an illustrative envelope, not a rolling forecast — say so in the caption.

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen } from '@testing-library/react'
import { ThemeProvider } from '../store/ThemeContext'
import PitaKetidakpastian from './PitaKetidakpastian'

test('renders median line and reference lines for Lebaran dates', () => {
  const data = [
    { t: '1 Jan', p10: 90, median: 100, p90: 115 },
    { t: '2 Jan', p10: 92, median: 101, p90: 130 },
  ]
  const { container } = render(
    <ThemeProvider><PitaKetidakpastian data={data} kondisi="normal" tinggi={200} lebaranX={['1 Jan']} /></ThemeProvider>
  )
  // Recharts renders <path> for areas/lines and reference lines
  expect(container.querySelectorAll('path.recharts-line-curve').length).toBeGreaterThanOrEqual(1)
  expect(container.querySelector('.recharts-reference-line')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/charts/PitaKetidakpastian.jsx`**

```jsx
import { ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'
import { useTokens, usePrefersReducedMotion } from '../store/ThemeContext'
import { TooltipKustom } from './tooltip'

export default function PitaKetidakpastian({ data, kondisi = 'normal', tinggi = 360, lebaranX = [] }) {
  const t = useTokens(); const reduced = usePrefersReducedMotion()
  const hue = kondisi === 'lebaran' ? t.cat3 : t.cat2
  const id = `pita-${kondisi}`

  // stack the band as low + (high-low) so Area draws a ribbon between p10 and p90
  const rows = data.map((d) => ({ ...d, base: d.p10, span: d.p90 - d.p10 }))

  return (
    <ResponsiveContainer width="100%" height={tinggi}>
      <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 8, left: 4 }} stackOffset="none">
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={hue} stopOpacity={0.22} />
            <stop offset="50%" stopColor={hue} stopOpacity={0.08} />
            <stop offset="100%" stopColor={hue} stopOpacity={0.22} />
          </linearGradient>
          {kondisi === 'lebaran' && (
            <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke={t.inkMuted} strokeOpacity="0.3" strokeWidth="1" />
            </pattern>
          )}
        </defs>
        <CartesianGrid stroke={t.line} vertical={false} />
        <XAxis dataKey="t" tick={{ fill: t.inkMuted, fontSize: 11 }} minTickGap={48} />
        <YAxis tick={{ fill: t.inkMuted, fontSize: 11 }} width={64} tickFormatter={(v) => v.toLocaleString('id-ID')} />
        <Tooltip content={<TooltipKustom />} />
        <Area dataKey="base" stackId="pita" stroke="none" fill="transparent" legendType="none" isAnimationActive={!reduced} />
        <Area dataKey="span" stackId="pita" stroke={hue} strokeOpacity={0.5} strokeWidth={1}
          fill={`url(#${id})`} name="rentang p10–p90" isAnimationActive={!reduced} />
        {kondisi === 'lebaran' && (
          <Area dataKey="span" stackId="pita2" stroke="none" fill="url(#hatch)" legendType="none" tooltipType="none" isAnimationActive={false} />
        )}
        <Line dataKey="median" name="median" stroke={t.signature} strokeWidth={1.5} dot={false} strokeLinecap="round" isAnimationActive={!reduced} />
        {lebaranX.map((x) => (
          <ReferenceLine key={x} x={x} stroke={t.line} strokeDasharray="2 4"
            label={{ value: 'Lebaran', position: 'top', fill: t.inkMuted, fontSize: 10, fontFamily: 'var(--font-mono)' }} />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  )
}
```

- [ ] **Step 4: Run — `npm test`** → PASS.

- [ ] **Step 5: Implement `src/sections/Hero.jsx`**

```jsx
import { useData } from '../store/DataContext'
import { useFilter } from '../store/FilterContext'
import { buildEnvelope } from '../lib/series'
import { offsetToDate, formatTanggal, indexOfDate } from '../store/dates'
import ChartFrame from '../charts/ChartFrame'
import PitaKetidakpastian from '../charts/PitaKetidakpastian'
import StatTile from '../components/StatTile'

const LEBARAN = ['2025-03-31', '2026-03-21']

export default function Hero() {
  const { data: harga } = useData('harga.json')
  const { data: band } = useData('band.json')
  const { data: meta } = useData('meta.json')
  const { komoditas } = useFilter()
  if (!harga || !band || !meta) return <div style={{ minHeight: 420 }} />

  const b = band.komoditas[komoditas]?.normal
  const avg = buildEnvelope(harga.komoditas[komoditas] || {}).map((e) => e.avg)
  const rows = avg.map((v, i) => {
    if (v == null) return null
    return {
      t: formatTanggal(offsetToDate(harga.tanggal_awal, i), { pendek: true }),
      p10: Math.round(v * (1 + b.p10 / 100)),
      median: Math.round(v),
      p90: Math.round(v * (1 + b.p90 / 100)),
    }
  }).filter(Boolean)
  const lebaranX = LEBARAN
    .map((d) => rows[indexOfDate(harga.tanggal_awal, d)]?.t)
    .filter(Boolean)

  return (
    <div style={{ padding: '2.5rem 0 1rem' }}>
      <p className="eyebrow">Rentang, bukan titik</p>
      <h1 style={{ fontSize: 'clamp(1.75rem, 4vw, 2.75rem)', lineHeight: 1.15, maxWidth: '20ch' }}>
        Yang bisa diprediksi dari harga sayur bukan angka pastinya, tapi seberapa lebar kemungkinannya bergerak.
      </h1>
      <ChartFrame
        caption={`Ilustrasi: garis = harga rata-rata ${komoditas}; pita = ±rentang historis 7-hari (p10–p90). Bukan prediksi bergulir.`}
        tabel={{ kolom: ['Tanggal', 'p10', 'Median', 'p90'], baris: rows.filter((_, i) => i % 21 === 0).map((r) => [r.t, r.p10, r.median, r.p90]) }}
      >
        <PitaKetidakpastian data={rows} kondisi="normal" tinggi={360} lebaranX={lebaranX} />
      </ChartFrame>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <StatTile label="Komoditas" value={meta.komoditas.length} />
        <StatTile label="Pasar" value={meta.pasar.length} />
        <StatTile label="Bulan data" value={Math.round(indexOfDate(meta.tanggal_data_awal, meta.tanggal_data_terakhir) / 30)} />
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Verify visually** — hero ribbon draws, widens where the historical band is wide, Lebaran reference lines visible.

- [ ] **Step 7: Commit** — `git commit -am "feat: PitaKetidakpastian signature + Hero section"`

---

## Task 11: CurahHujanChart + SuhuChart + CuacaKurs section

**Files:**
- Create: `src/charts/CurahHujanChart.jsx`, `src/charts/SuhuChart.jsx`
- Modify: `src/sections/CuacaKurs.jsx`
- Create: `src/sections/CuacaKurs.test.jsx`

**Interfaces:**
- Consumes: `useData('cuaca.json')` shape `{tanggal_awal, pasar: {[pasar]: {curah_hujan_mm:[], suhu_avg:[], suhu_min:[], suhu_max:[]}}}`; `useFilter` (pasar; if `__semua__`, default to `meta.pasar[0]` and show a note).
- Produces: `<CurahHujanChart pasar />`, `<SuhuChart pasar />`.

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen, waitFor } from '@testing-library/react'
import { DataProvider } from '../store/DataContext'
import { FilterProvider } from '../store/FilterContext'
import { ThemeProvider } from '../store/ThemeContext'
import CuacaKurs from './CuacaKurs'

beforeEach(() => vi.stubGlobal('fetch', vi.fn((u) => Promise.resolve({ ok: true, json: () => Promise.resolve(
  String(u).includes('cuaca') ? { tanggal_awal: '2024-08-22', pasar: { A: { curah_hujan_mm: [0, 5, 12], suhu_avg: [24, 25, 23], suhu_min: [20, 21, 19], suhu_max: [30, 31, 29] } } }
  : String(u).includes('meta') ? { pasar: ['A'], komoditas: [{ nama: 'X', kategori: 'c', caveat_data: false }] }
  : String(u).includes('kurs') ? { tanggal_awal: '2024-08-22', kurs_usd_idr: [15600, 15650, 15700] }
  : {}) })))

const wrap = (ui) => <ThemeProvider><DataProvider><FilterProvider>{ui}</FilterProvider></DataProvider></ThemeProvider>

test('renders separate rain, temp, kurs charts (no dual axis)', async () => {
  render(wrap(<CuacaKurs />))
  await waitFor(() => expect(screen.getByText(/Curah Hujan/i)).toBeInTheDocument())
  expect(screen.getByText(/Suhu/i)).toBeInTheDocument()
  expect(screen.getByText(/Kurs USD\/IDR/i)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/charts/CurahHujanChart.jsx`**

```jsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useData } from '../store/DataContext'
import { useTokens, usePrefersReducedMotion } from '../store/ThemeContext'
import { offsetToDate, formatTanggal } from '../store/dates'
import ChartFrame from './ChartFrame'
import { TooltipKustom } from './tooltip'

export default function CurahHujanChart({ pasar }) {
  const { data } = useData('cuaca.json')
  const t = useTokens(); const reduced = usePrefersReducedMotion()
  if (!data) return null
  const c = data.pasar[pasar]; if (!c) return null
  const rows = c.curah_hujan_mm.map((v, i) => ({ t: formatTanggal(offsetToDate(data.tanggal_awal, i), { pendek: true }), hujan: v }))
  return (
    <ChartFrame judul={`Curah Hujan — ${pasar}`} caption="mm per hari (Open-Meteo, data aktual historis)."
      tabel={{ kolom: ['Tanggal', 'Curah hujan (mm)'], baris: rows.filter((_, i) => i % 14 === 0).map((r) => [r.t, r.hujan]) }}>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
          <CartesianGrid stroke={t.line} vertical={false} />
          <XAxis dataKey="t" tick={{ fill: t.inkMuted, fontSize: 11 }} minTickGap={48} />
          <YAxis tick={{ fill: t.inkMuted, fontSize: 11 }} width={48} />
          <Tooltip content={<TooltipKustom />} />
          <Bar dataKey="hujan" name="curah hujan" fill={t.rain} radius={[4, 4, 0, 0]} isAnimationActive={!reduced} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
```

- [ ] **Step 4: Implement `src/charts/SuhuChart.jsx`** (ComposedChart: Area min–max + Line avg)

```jsx
import { ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useData } from '../store/DataContext'
import { useTokens, usePrefersReducedMotion } from '../store/ThemeContext'
import { offsetToDate, formatTanggal } from '../store/dates'
import ChartFrame from './ChartFrame'
import { TooltipKustom } from './tooltip'

export default function SuhuChart({ pasar }) {
  const { data } = useData('cuaca.json')
  const t = useTokens(); const reduced = usePrefersReducedMotion()
  if (!data) return null
  const c = data.pasar[pasar]; if (!c) return null
  const rows = c.suhu_avg.map((v, i) => ({
    t: formatTanggal(offsetToDate(data.tanggal_awal, i), { pendek: true }),
    avg: v, lo: c.suhu_min[i], span: (c.suhu_max[i] ?? 0) - (c.suhu_min[i] ?? 0),
  }))
  return (
    <ChartFrame judul={`Suhu — ${pasar}`} caption="°C: garis = rata-rata, pita = min–max harian."
      tabel={{ kolom: ['Tanggal', 'Min', 'Rata-rata', 'Max'], baris: rows.filter((_, i) => i % 14 === 0).map((r, i2) => [r.t, r.lo, r.avg, c.suhu_max[i2 * 14]]) }}>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
          <CartesianGrid stroke={t.line} vertical={false} />
          <XAxis dataKey="t" tick={{ fill: t.inkMuted, fontSize: 11 }} minTickGap={48} />
          <YAxis tick={{ fill: t.inkMuted, fontSize: 11 }} width={40} unit="°" />
          <Tooltip content={<TooltipKustom />} />
          <Legend />
          <Area dataKey="lo" stackId="s" stroke="none" fill="transparent" legendType="none" isAnimationActive={!reduced} />
          <Area dataKey="span" stackId="s" stroke="none" fill={t.temp} fillOpacity={0.12} name="rentang min–max" isAnimationActive={!reduced} />
          <Line dataKey="avg" name="suhu rata-rata" stroke={t.temp} strokeWidth={2} dot={false} isAnimationActive={!reduced} />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
```

- [ ] **Step 5: Implement `src/sections/CuacaKurs.jsx`**

```jsx
import { useData } from '../store/DataContext'
import { useFilter } from '../store/FilterContext'
import CurahHujanChart from '../charts/CurahHujanChart'
import SuhuChart from '../charts/SuhuChart'
import KursChart from '../charts/KursChart'

export default function CuacaKurs() {
  const { data: meta } = useData('meta.json')
  const { pasar } = useFilter()
  if (!meta) return <p className="mono">Memuat…</p>
  const p = pasar === '__semua__' ? meta.pasar[0] : pasar
  return (
    <>
      <p className="eyebrow">Cuaca &amp; Kurs</p>
      <h2>Kondisi lingkungan</h2>
      <p style={{ color: 'var(--ink-muted)', maxWidth: '60ch' }}>
        {pasar === '__semua__' && `Menampilkan ${p} (pilih pasar spesifik di bilah atas). `}
        Fitur cuaca &amp; kurs <strong>tidak menambah akurasi prediksi harga</strong> di horizon yang diuji — lihat Ringkasan Riset.
      </p>
      <CurahHujanChart pasar={p} />
      <SuhuChart pasar={p} />
      <KursChart />
    </>
  )
}
```

- [ ] **Step 6: Run — `npm test`** → PASS. Visual check.

- [ ] **Step 7: Commit** — `git commit -am "feat: CuacaKurs section — rain, temp, kurs (separate axes)"`

---

## Task 12: rekomendasi.js (port of the Python band logic)

**Files:**
- Create: `src/lib/rekomendasi.js`, `src/lib/rekomendasi.test.js`

**Interfaces:**
- Produces: `rekomendasiBand(band: {p10,median,p90,lebar_band,n}, hargaSekarang: number, kondisi: 'normal'|'dekat_lebaran') → {rentang: [number, number], median: number, arah: string, ketidakpastian: string, saran: string, peringatanSampel: string|null}`

> Port `scripts/rekomendasi_band_h7.py::rekomendasi()` exactly: median>3 → NAIK, <-3 → TURUN, else stabil; `lebar_band` >30 → "TINGGI" + "sulit dioptimalkan"; >15 → "sedang"; else "rendah". `kondisi==='dekat_lebaran'` always appends the small-sample warning.

- [ ] **Step 1: Write the failing test**

```js
import { rekomendasiBand } from './rekomendasi'

test('band lebar → ketidakpastian TINGGI, tidak bilang stabil polos', () => {
  const r = rekomendasiBand({ p10: -30, median: 0, p90: 37.1, lebar_band: 67.1, n: 395 }, 35000, 'dekat_lebaran')
  expect(r.rentang).toEqual([24500, 48000])   // 35000*(1-0.3), 35000*(1+0.371) rounded
  expect(r.ketidakpastian).toMatch(/TINGGI/)
  expect(r.saran).toMatch(/sulit dioptimalkan/i)
  expect(r.peringatanSampel).toMatch(/2 kejadian/)
})
test('median > 3 → arah NAIK', () => {
  const r = rekomendasiBand({ p10: -33.3, median: 7.7, p90: 50, lebar_band: 83.3, n: 396 }, 80000, 'dekat_lebaran')
  expect(r.arah).toMatch(/NAIK/)
})
test('kondisi normal → tidak ada peringatan sampel', () => {
  const r = rekomendasiBand({ p10: -6, median: 0, p90: 6, lebar_band: 12, n: 5000 }, 18000, 'normal')
  expect(r.peringatanSampel).toBeNull()
  expect(r.ketidakpastian).toMatch(/rendah/)
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/lib/rekomendasi.js`**

```js
export function rekomendasiBand(b, hargaSekarang, kondisi) {
  const abs = (pct) => Math.round(hargaSekarang * (1 + pct / 100))
  const rentang = [abs(b.p10), abs(b.p90)]
  const median = abs(b.median)
  const lebar = b.lebar_band

  const arah = b.median > 3 ? 'median historis cenderung NAIK'
    : b.median < -3 ? 'median historis cenderung TURUN'
    : 'median historis relatif stabil'

  let ketidakpastian, saran
  if (lebar > 30) {
    ketidakpastian = 'Ketidakpastian TINGGI — rentang sangat lebar, median saja tidak cukup mewakili.'
    saran = 'Waktu jual sulit dioptimalkan dari data historis saja di kondisi ini — pertimbangkan faktor lain (kebutuhan modal, kapasitas simpan hasil panen).'
  } else if (lebar > 15) {
    ketidakpastian = 'Ketidakpastian sedang — perhatikan rentangnya, jangan cuma patokan ke median.'
    saran = b.median > 3 ? 'Pertimbangkan TUNGGU (dengan waspada).'
      : b.median < -3 ? 'Pertimbangkan JUAL SEKARANG (dengan waspada).'
      : 'Harga cenderung stabil, tapi tetap ada variasi — waktu jual tidak terlalu krusial.'
  } else {
    ketidakpastian = 'Ketidakpastian relatif rendah — median cukup representatif.'
    saran = b.median > 3 ? 'Pertimbangkan TUNGGU.'
      : b.median < -3 ? 'Pertimbangkan JUAL SEKARANG.'
      : 'Harga stabil — waktu jual tidak banyak berpengaruh.'
  }

  const peringatanSampel = kondisi === 'dekat_lebaran'
    ? 'PERINGATAN: estimasi kondisi Lebaran ini cuma didasarkan pada 2 kejadian dalam data (Lebaran 2025 & 2026) — sampel sangat kecil untuk pola musiman, dan beberapa komoditas menunjukkan pola berbeda antara kedua tahun itu. Anggap sebagai indikasi awal, bukan pola pasti.'
    : null

  return { rentang, median, arah, ketidakpastian, saran, peringatanSampel }
}
```

- [ ] **Step 4: Run — `npm test`** → PASS.

- [ ] **Step 5: Commit** — `git commit -am "feat: port band recommendation logic to JS"`

---

## Task 13: PrediksiChip + BannerKejujuran + BacktestChart + MaeHorizonChart + PrediksiModel section

**Files:**
- Create: `src/components/PrediksiChip.jsx`, `src/components/BannerKejujuran.jsx`, `src/charts/BacktestChart.jsx`, `src/charts/MaeHorizonChart.jsx`
- Modify: `src/sections/PrediksiModel.jsx`
- Create: `src/sections/PrediksiModel.test.jsx`

**Interfaces:**
- Consumes:
  - `useData('prediksi.json')` → `{tanggal_anchor_range, baris: [...]}` (rows per §4 of PRD)
  - `useData('backtest.json')` → `{horizon:7, komoditas: {[nama]: {[pasar]: {tanggal:[], aktual:[], model:[], baseline:[]}}}}`
  - `useData('riset.json')` → `{horizon_direct: [{horizon, mae_model, mae_baseline, selisih_pct}], ...}`
  - `maeDeret`
- Produces: `<PrediksiChip row={prediksiBaris} pasar />`, `<BannerKejujuran tanggal />`.

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen, waitFor } from '@testing-library/react'
import { DataProvider } from '../store/DataContext'
import { FilterProvider } from '../store/FilterContext'
import { ThemeProvider } from '../store/ThemeContext'
import PrediksiModel from './PrediksiModel'

const PRED = { tanggal_anchor_range: ['2026-08-16','2026-08-22'], baris: [
  { pasar: 'Pasar Banjaran', komoditas: 'CABE MERAH KERITING', tanggal_anchor: '2026-08-22', harga_terakhir: 35000,
    tanggal_target_h1: '2026-08-23', pred_model_h1: 35011, pred_baseline_h1: 35000, mae_model_hist_h1: 619, mae_baseline_hist_h1: 460, model_lebih_buruk_pct_h1: 34.5,
    tanggal_target_h3: '2026-08-25', pred_model_h3: 34945, pred_baseline_h3: 35000, mae_model_hist_h3: 1181, mae_baseline_hist_h3: 939, model_lebih_buruk_pct_h3: 25.7,
    tanggal_target_h7: '2026-08-29', pred_model_h7: 35111, pred_baseline_h7: 35000, mae_model_hist_h7: 2231, mae_baseline_hist_h7: 1592, model_lebih_buruk_pct_h7: 40.1 } ] }
const RISET = { horizon_direct: [{ horizon: 1, mae_model: 619, mae_baseline: 460, selisih_pct: 34.5 }], horizon_recursive: [], tahapan: [], kesimpulan: '' }
const META = { komoditas: [{ nama: 'CABE MERAH KERITING', kategori: 'cabai', caveat_data: false }], pasar: ['Pasar Banjaran'], tanggal_data_terakhir: '2026-08-22' }

beforeEach(() => vi.stubGlobal('fetch', vi.fn((u) => Promise.resolve({ ok: true, json: () => Promise.resolve(
  String(u).includes('prediksi') ? PRED : String(u).includes('riset') ? RISET : String(u).includes('meta') ? META
  : String(u).includes('backtest') ? { horizon: 7, komoditas: {} } : {}) }))))

const wrap = (ui) => <ThemeProvider><DataProvider><FilterProvider>{ui}</FilterProvider></DataProvider></ThemeProvider>

test('prediksi chip shows model paired with baseline + MAE label; banner shows anchor date', async () => {
  render(wrap(<PrediksiModel />))
  await waitFor(() => expect(screen.getByText(/dihitung dari data terakhir/i)).toBeInTheDocument())
  expect(screen.getByText(/22 Agu 2026/)).toBeInTheDocument()
  expect(screen.getAllByText(/35\.000/).length).toBeGreaterThan(0)   // baseline
  expect(screen.getAllByText(/35\.111/).length).toBeGreaterThan(0)   // model H+7
  expect(screen.getAllByText(/\+40/).length).toBeGreaterThan(0)      // "+40% MAE" label
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/components/BannerKejujuran.jsx`**

```jsx
import { formatTanggal } from '../store/dates'
export default function BannerKejujuran({ tanggal }) {
  return (
    <div className="mono" style={{ background: 'var(--surface-2)', borderLeft: '3px solid var(--brand)', padding: '10px 14px', fontSize: '.8rem', margin: '12px 0' }}>
      Prediksi dihitung dari data terakhir {formatTanggal(tanggal, { pendek: true })}, bukan hari ini.
      Model ML secara historis <strong>kurang akurat dari baseline</strong> "harga besok ≈ harga hari ini" —
      ditampilkan sebagai pembanding, bukan angka otoritatif.
    </div>
  )
}
```

- [ ] **Step 4: Implement `src/components/PrediksiChip.jsx`**

```jsx
import { formatTanggal } from '../store/dates'
const rp = (v) => 'Rp ' + Math.round(v).toLocaleString('id-ID')

function Horizon({ label, tgl, model, baseline, worse }) {
  return (
    <div style={{ borderTop: '1px solid var(--line)', padding: '8px 0' }}>
      <div className="mono" style={{ fontSize: '.7rem', color: 'var(--ink-muted)' }}>{label} · {formatTanggal(tgl, { pendek: true })}</div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'baseline', marginTop: 2 }}>
        <span style={{ display: 'inline-flex', gap: 5, alignItems: 'baseline' }}>
          <span style={{ width: 7, height: 7, borderRadius: 2, background: 'var(--cat-3)' }} />
          <strong className="mono">{rp(model)}</strong>
        </span>
        <span className="mono" style={{ color: 'var(--ink-muted)', fontSize: '.85rem' }}>
          baseline {rp(baseline)}
        </span>
      </div>
      <div className="mono" style={{ fontSize: '.68rem', color: 'var(--ink-muted)' }}>model historis +{worse}% MAE</div>
    </div>
  )
}

export default function PrediksiChip({ row }) {
  if (!row) return (
    <div className="panel" style={{ padding: 14 }}>
      <div className="mono" style={{ fontSize: '.8rem' }}>Data tidak tersedia</div>
      <div className="mono" style={{ fontSize: '.7rem', color: 'var(--ink-muted)' }}>pasar ini jarang melaporkan komoditas ini</div>
    </div>
  )
  return (
    <div className="panel" style={{ padding: 14 }}>
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600 }}>{row.pasar}</div>
      <div className="mono" style={{ fontSize: '.7rem', color: 'var(--ink-muted)' }}>terakhir {rp(row.harga_terakhir)} ({formatTanggal(row.tanggal_anchor, { pendek: true })})</div>
      <Horizon label="H+1" tgl={row.tanggal_target_h1} model={row.pred_model_h1} baseline={row.pred_baseline_h1} worse={row.model_lebih_buruk_pct_h1} />
      <Horizon label="H+3" tgl={row.tanggal_target_h3} model={row.pred_model_h3} baseline={row.pred_baseline_h3} worse={row.model_lebih_buruk_pct_h3} />
      <Horizon label="H+7" tgl={row.tanggal_target_h7} model={row.pred_model_h7} baseline={row.pred_baseline_h7} worse={row.model_lebih_buruk_pct_h7} />
    </div>
  )
}
```

- [ ] **Step 5: Implement `src/charts/BacktestChart.jsx`**

```jsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useTokens, usePrefersReducedMotion } from '../store/ThemeContext'
import { maeDeret } from '../lib/stats'
import ChartFrame from './ChartFrame'
import { TooltipKustom } from './tooltip'
import { formatTanggal } from '../store/dates'

export default function BacktestChart({ seri, komoditas, pasar }) {
  const t = useTokens(); const reduced = usePrefersReducedMotion()
  if (!seri) return <p className="mono">Tidak ada data backtest untuk {komoditas} @ {pasar}.</p>
  const rows = seri.tanggal.map((d, i) => ({
    t: formatTanggal(d, { pendek: true }), aktual: seri.aktual[i], model: seri.model[i], baseline: seri.baseline[i],
  }))
  const maeM = Math.round(maeDeret(seri.aktual, seri.model))
  const maeB = Math.round(maeDeret(seri.aktual, seri.baseline))
  return (
    <ChartFrame judul={`Backtest H+7 — ${komoditas} @ ${pasar}`}
      caption={`Periode uji 60 hari. MAE model Rp ${maeM.toLocaleString('id-ID')} · baseline Rp ${maeB.toLocaleString('id-ID')}.`}
      tabel={{ kolom: ['Tanggal', 'Aktual', 'Model', 'Baseline'], baris: rows.map((r) => [r.t, r.aktual, r.model, r.baseline]) }}>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
          <CartesianGrid stroke={t.line} vertical={false} />
          <XAxis dataKey="t" tick={{ fill: t.inkMuted, fontSize: 11 }} minTickGap={40} />
          <YAxis tick={{ fill: t.inkMuted, fontSize: 11 }} width={72} tickFormatter={(v) => 'Rp ' + v.toLocaleString('id-ID')} />
          <Tooltip content={<TooltipKustom />} />
          <Legend />
          <Line dataKey="aktual" name="aktual" stroke={t.ink} strokeWidth={2.5} dot={false} isAnimationActive={!reduced} />
          <Line dataKey="model" name="model" stroke={t.cat3} strokeWidth={2} dot={false} isAnimationActive={!reduced} />
          <Line dataKey="baseline" name="baseline" stroke={t.inkMuted} strokeWidth={2} strokeDasharray="4 2" dot={false} isAnimationActive={!reduced} />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
```

- [ ] **Step 6: Implement `src/charts/MaeHorizonChart.jsx`**

```jsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, LabelList, ResponsiveContainer } from 'recharts'
import { useTokens, usePrefersReducedMotion } from '../store/ThemeContext'
import ChartFrame from './ChartFrame'
import { TooltipKustom } from './tooltip'

export default function MaeHorizonChart({ horizonDirect }) {
  const t = useTokens(); const reduced = usePrefersReducedMotion()
  const rows = horizonDirect.map((h) => ({ h: `H+${h.horizon}`, model: h.mae_model, baseline: h.mae_baseline, pct: h.selisih_pct }))
  return (
    <ChartFrame judul="MAE model vs baseline per horizon (direct)" caption="Model kalah di semua horizon."
      tabel={{ kolom: ['Horizon', 'MAE model', 'MAE baseline', 'Selisih %'], baris: rows.map((r) => [r.h, r.model, r.baseline, r.pct]) }}>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={rows} margin={{ top: 16, right: 12, bottom: 8, left: 4 }} barGap={6}>
          <CartesianGrid stroke={t.line} vertical={false} />
          <XAxis dataKey="h" tick={{ fill: t.inkMuted, fontSize: 12 }} />
          <YAxis tick={{ fill: t.inkMuted, fontSize: 11 }} width={64} tickFormatter={(v) => v.toLocaleString('id-ID')} />
          <Tooltip content={<TooltipKustom />} />
          <Legend />
          <Bar dataKey="model" name="model" fill={t.cat3} radius={[4, 4, 0, 0]} isAnimationActive={!reduced}>
            <LabelList dataKey="pct" position="top" formatter={(v) => `+${v}%`} style={{ fill: t.inkMuted, fontFamily: 'var(--font-mono)', fontSize: 11 }} />
          </Bar>
          <Bar dataKey="baseline" name="baseline persistence" fill={t.inkMuted} radius={[4, 4, 0, 0]} isAnimationActive={!reduced} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
```

- [ ] **Step 7: Implement `src/sections/PrediksiModel.jsx`**

```jsx
import { useData } from '../store/DataContext'
import { useFilter } from '../store/FilterContext'
import BannerKejujuran from '../components/BannerKejujuran'
import PrediksiChip from '../components/PrediksiChip'
import BacktestChart from '../charts/BacktestChart'
import MaeHorizonChart from '../charts/MaeHorizonChart'

export default function PrediksiModel() {
  const { data: pred } = useData('prediksi.json')
  const { data: backtest } = useData('backtest.json')
  const { data: riset } = useData('riset.json')
  const { data: meta } = useData('meta.json')
  const { komoditas, pasar } = useFilter()
  if (!pred || !backtest || !riset || !meta) return <p className="mono">Memuat…</p>

  const barisKom = pred.baris.filter((r) => r.komoditas === komoditas)
  const byPasar = Object.fromEntries(barisKom.map((r) => [r.pasar, r]))
  const seri = backtest.komoditas[komoditas]?.[pasar === '__semua__' ? meta.pasar[0] : pasar]

  return (
    <>
      <p className="eyebrow">Prediksi Model</p>
      <h2>Apa yang model ML katakan — dan seberapa akurat</h2>
      <BannerKejujuran tanggal={meta.tanggal_data_terakhir} />

      <h3>Backtest (uji pada data yang sudah lewat)</h3>
      <BacktestChart seri={seri} komoditas={komoditas} pasar={pasar === '__semua__' ? meta.pasar[0] : pasar} />

      <h3>Prediksi ke depan — {komoditas}</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12, margin: '12px 0' }}>
        {meta.pasar.map((p) => <PrediksiChip key={p} row={byPasar[p]} />)}
      </div>

      <h3>Ringkasan akurasi per horizon</h3>
      <MaeHorizonChart horizonDirect={riset.horizon_direct} />
    </>
  )
}
```

- [ ] **Step 8: Run — `npm test`** → PASS. Visual check: chips show model+baseline+label, banner visible, backtest 3 lines, MAE bars.

- [ ] **Step 9: Commit** — `git commit -am "feat: PrediksiModel section — backtest, forward chips, MAE"`

---

## Task 14: BandKomoditasChart + kalkulator + RekomendasiBand section

**Files:**
- Create: `src/charts/BandKomoditasChart.jsx`
- Modify: `src/sections/RekomendasiBand.jsx`
- Create: `src/sections/RekomendasiBand.test.jsx`

**Interfaces:**
- Consumes: `useData('band.json')`, `useFilter`, `rekomendasiBand`, `<PitaKetidakpastian>` (reused for a static single-band view), tokens.
- Produces: `<BandKomoditasChart band={band.json} />` — horizontal range plot, all 25 commodities, normal vs Lebaran.

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { DataProvider } from '../store/DataContext'
import { FilterProvider } from '../store/FilterContext'
import { ThemeProvider } from '../store/ThemeContext'
import RekomendasiBand from './RekomendasiBand'

const BAND = { horizon: 7, komoditas: { 'CABE MERAH KERITING': {
  normal: { p10: -16.7, p25: -8.3, median: 0, p75: 9.4, p90: 25, lebar_band: 41.7, n: 5032 },
  dekat_lebaran: { p10: -30, p25: -20, median: 0, p75: 20, p90: 37.1, lebar_band: 67.1, n: 395 } } } }

beforeEach(() => vi.stubGlobal('fetch', vi.fn((u) => Promise.resolve({ ok: true, json: () => Promise.resolve(
  String(u).includes('band') ? BAND : String(u).includes('meta') ? { komoditas: [{ nama: 'CABE MERAH KERITING', kategori: 'cabai', caveat_data: false }], pasar: ['A'] } : {}) }))))

const wrap = (ui) => <ThemeProvider><DataProvider><FilterProvider>{ui}</FilterProvider></DataProvider></ThemeProvider>

test('kalkulator: input harga → rentang + peringatan Lebaran', async () => {
  render(wrap(<RekomendasiBand />))
  await waitFor(() => expect(screen.getByLabelText(/harga sekarang/i)).toBeInTheDocument())
  fireEvent.change(screen.getByLabelText(/harga sekarang/i), { target: { value: '35000' } })
  fireEvent.click(screen.getByLabelText(/menjelang lebaran/i))
  expect(screen.getByText(/Rp 24\.500/)).toBeInTheDocument()
  expect(screen.getByText(/Rp 48\.000/)).toBeInTheDocument()
  expect(screen.getByText(/2 kejadian/)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/charts/BandKomoditasChart.jsx`**

```jsx
import { ComposedChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer, ErrorBar } from 'recharts'
import { useTokens, usePrefersReducedMotion } from '../store/ThemeContext'
import ChartFrame from './ChartFrame'
import { TooltipKustom } from './tooltip'

export default function BandKomoditasChart({ band }) {
  const t = useTokens(); const reduced = usePrefersReducedMotion()
  const names = Object.keys(band.komoditas).sort()
  const mk = (kondisi) => names.map((n) => {
    const b = band.komoditas[n]?.[kondisi]
    if (!b) return null
    return { nama: n, median: b.median, err: [b.median - b.p10, b.p90 - b.median] }
  }).filter(Boolean)
  const normal = mk('normal'); const lebaran = mk('dekat_lebaran')

  return (
    <ChartFrame judul="Lebar sebaran pergerakan harga 7-hari per komoditas"
      caption="Titik = median %, garis = p10–p90. Biru = normal, amber = menjelang Lebaran."
      tabel={{ kolom: ['Komoditas', 'Median normal %', 'Median Lebaran %'],
        baris: names.map((n) => [n, band.komoditas[n]?.normal?.median ?? '—', band.komoditas[n]?.dekat_lebaran?.median ?? '—']) }}>
      <ResponsiveContainer width="100%" height={Math.max(360, names.length * 22)}>
        <ComposedChart layout="vertical" data={normal} margin={{ top: 8, right: 16, bottom: 8, left: 120 }}>
          <CartesianGrid stroke={t.line} horizontal={false} />
          <XAxis type="number" tick={{ fill: t.inkMuted, fontSize: 11 }} unit="%" />
          <YAxis type="category" dataKey="nama" width={116} tick={{ fill: t.inkMuted, fontSize: 10 }} />
          <ReferenceLine x={0} stroke={t.inkMuted} strokeDasharray="2 4" />
          <Tooltip content={<TooltipKustom />} />
          <Legend />
          <Scatter name="normal" data={normal} fill={t.cat1} isAnimationActive={!reduced}>
            <ErrorBar dataKey="err" width={4} strokeWidth={3} stroke={t.cat1} direction="x" />
          </Scatter>
          <Scatter name="menjelang Lebaran" data={lebaran} fill={t.cat3} isAnimationActive={!reduced}>
            <ErrorBar dataKey="err" width={4} strokeWidth={3} stroke={t.cat3} direction="x" />
          </Scatter>
        </ComposedChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
```

- [ ] **Step 4: Implement `src/sections/RekomendasiBand.jsx`**

```jsx
import { useState } from 'react'
import { useData } from '../store/DataContext'
import { useFilter } from '../store/FilterContext'
import { rekomendasiBand } from '../lib/rekomendasi'
import BandKomoditasChart from '../charts/BandKomoditasChart'

const rp = (v) => 'Rp ' + Math.round(v).toLocaleString('id-ID')

export default function RekomendasiBand() {
  const { data: band } = useData('band.json')
  const { komoditas } = useFilter()
  const [harga, setHarga] = useState(35000)
  const [lebaran, setLebaran] = useState(false)
  if (!band) return <p className="mono">Memuat…</p>

  const kondisi = lebaran ? 'dekat_lebaran' : 'normal'
  const b = band.komoditas[komoditas]?.[kondisi]
  const r = b && harga ? rekomendasiBand(b, Number(harga), kondisi) : null

  return (
    <>
      <p className="eyebrow">Rekomendasi</p>
      <h2>Rentang harga 7 hari ke depan — bukan prediksi titik</h2>
      <p style={{ color: 'var(--ink-muted)', maxWidth: '60ch' }}>
        Dari distribusi historis pergerakan harga (bukan model ML). Yang berubah menjelang Lebaran
        adalah <em>lebar rentang</em>, bukan titik tengahnya.
      </p>

      <div className="panel" style={{ padding: 16, margin: '16px 0', maxWidth: 460 }}>
        <label className="mono" style={{ display: 'block', fontSize: '.8rem' }}>
          Harga {komoditas} sekarang (Rp)
          <input type="number" value={harga} onChange={(e) => setHarga(e.target.value)} aria-label={`harga ${komoditas} sekarang`}
            style={{ display: 'block', marginTop: 4, fontFamily: 'var(--font-mono)', fontSize: '1rem', padding: '6px 8px', width: 180, background: 'var(--surface)', color: 'var(--ink)', border: '1px solid var(--line)', borderRadius: 8 }} />
        </label>
        <label className="mono" style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 10, fontSize: '.85rem' }}>
          <input type="checkbox" checked={lebaran} onChange={(e) => setLebaran(e.target.checked)} aria-label="kondisi menjelang Lebaran" />
          Menjelang Lebaran (H-21 s/d H+7)
        </label>
        {r && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: '1.1rem' }}>
              {rp(r.rentang[0])} – {rp(r.rentang[1])}
            </div>
            <div className="mono" style={{ fontSize: '.8rem', color: 'var(--ink-muted)' }}>median {rp(r.median)} · {r.arah}</div>
            <p style={{ fontSize: '.9rem', marginTop: 6 }}>{r.ketidakpastian}</p>
            <p style={{ fontSize: '.9rem' }}>{r.saran}</p>
            {r.peringatanSampel && <p className="mono" style={{ fontSize: '.75rem', color: 'var(--ink-muted)' }}>{r.peringatanSampel}</p>}
          </div>
        )}
      </div>

      <BandKomoditasChart band={band} />
    </>
  )
}
```

- [ ] **Step 5: Run — `npm test`** → PASS. Visual: kalkulator updates live, band chart shows 25 rows.

- [ ] **Step 6: Commit** — `git commit -am "feat: RekomendasiBand section — kalkulator + band-per-komoditas chart"`

---

## Task 15: RingkasanRiset section

**Files:**
- Modify: `src/sections/RingkasanRiset.jsx`
- Create: `src/sections/RingkasanRiset.test.jsx`

**Interfaces:**
- Consumes: `useData('riset.json')` → `{tahapan: [{n, judul, isi}], horizon_direct: [], horizon_recursive: [], kesimpulan: string}`

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen, waitFor } from '@testing-library/react'
import { DataProvider } from '../store/DataContext'
import { ThemeProvider } from '../store/ThemeContext'
import RingkasanRiset from './RingkasanRiset'

beforeEach(() => vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({
  tahapan: [{ n: 1, judul: 'Bug data kotor', isi: 'detail' }],
  horizon_direct: [{ horizon: 1, mae_model: 619, mae_baseline: 460 }],
  horizon_recursive: [{ horizon: 'H+1', mae_model: 658, mae_baseline: 460 }],
  kesimpulan: 'Fitur tidak cukup.',
})}))))

test('renders numbered stages, horizon table, conclusion', async () => {
  render(<ThemeProvider><DataProvider><RingkasanRiset /></DataProvider></ThemeProvider>)
  await waitFor(() => expect(screen.getByText('Bug data kotor')).toBeInTheDocument())
  expect(screen.getByText(/Fitur tidak cukup/)).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: '619' })).toBeInTheDocument()
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `src/sections/RingkasanRiset.jsx`**

```jsx
import { useData } from '../store/DataContext'
import TabelView from '../components/TabelView'

export default function RingkasanRiset() {
  const { data: r } = useData('riset.json')
  if (!r) return <p className="mono">Memuat…</p>
  return (
    <>
      <p className="eyebrow">Ringkasan Riset</p>
      <h2>Delapan tahap menuji apakah model bisa memprediksi harga</h2>
      <ol style={{ paddingLeft: '1.2rem' }}>
        {r.tahapan.map((s) => (
          <li key={s.n} style={{ marginBottom: 12 }}>
            <strong>{s.judul}</strong>
            <p style={{ color: 'var(--ink-muted)', margin: '2px 0 0' }}>{s.isi}</p>
          </li>
        ))}
      </ol>
      <h3>MAE model vs baseline per horizon</h3>
      <TabelView kolom={['Horizon (direct)', 'MAE model', 'MAE baseline']}
        baris={r.horizon_direct.map((h) => [`H+${h.horizon}`, h.mae_model, h.mae_baseline])} />
      <TabelView kolom={['Horizon (recursive)', 'MAE model', 'MAE baseline']}
        baris={r.horizon_recursive.map((h) => [h.horizon, h.mae_model, h.mae_baseline])} />
      <h3>Kesimpulan</h3>
      <p style={{ maxWidth: '70ch' }}>{r.kesimpulan}</p>
    </>
  )
}
```

- [ ] **Step 4: Run — `npm test`** → PASS.

- [ ] **Step 5: Commit** — `git commit -am "feat: RingkasanRiset section"`

---

## Task 16: Accessibility + responsive pass

**Files:**
- Modify: `src/styles.css`, `src/App.jsx`, chart components as needed
- Create: `src/a11y.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
import { render, screen, waitFor } from '@testing-library/react'
import App from './App'
// reuse the App test's fetch stub (extract to a shared test helper: src/test-fixtures.js)

test('every section chart exposes a table view', async () => {
  render(<App />)
  await waitFor(() => expect(screen.getAllByText('Lihat sebagai tabel').length).toBeGreaterThanOrEqual(5))
})
test('nav links point to existing section ids', async () => {
  render(<App />)
  await waitFor(() => {
    document.querySelectorAll('nav a[href^="#"]').forEach((a) => {
      expect(document.getElementById(a.getAttribute('href').slice(1))).toBeInTheDocument()
    })
  })
})
```

- [ ] **Step 2: Run** → likely FAIL (missing shared fixture / some chart missing table).

- [ ] **Step 3: Extract `src/test-fixtures.js`** — one `stubFetchAll()` returning realistic mini-payloads for all 8 JSON files; use it in every section test (DRY).

- [ ] **Step 4: Fixes**
  - Add `role="img"` + `aria-label` to each `<ResponsiveContainer>` wrapper (`<div role="img" aria-label="...">`).
  - Ensure every chart is wrapped in `ChartFrame` with a `tabel` prop (audit each).
  - `styles.css`: add mobile rules — `@media (max-width: 640px)` → sub-bar selectors stack, nav becomes `overflow-x:auto; white-space:nowrap`, chart panels `padding: 10px`.
  - Add `@media (prefers-reduced-transparency: reduce)` → `.recharts-area-area { fill-opacity: 0.2 !important; }` for the ribbon.
  - Verify text contrast: `--ink-muted` on `--bg` ≥ 4.5:1 both themes (adjust hex in tokens if needed; re-run `tokens.test.js`).

- [ ] **Step 5: Run — `npm test`** → PASS. Manual: resize to 360px, tab through controls (focus ring visible), toggle OS reduced-motion.

- [ ] **Step 6: Commit** — `git commit -am "chore: accessibility + responsive pass"`

---

## Task 17: Build config, README, deploy

**Files:**
- Modify: `vite.config.js`, `package.json`
- Create: `README.md`, `.github/workflows/deploy.yml` (optional)

- [ ] **Step 1: Confirm `npm run build`** succeeds; open `dist/index.html` via `npm run preview`; all sections render from `public/data`.

- [ ] **Step 2: `README.md`**

```markdown
# Dashboard Harga Hasil Bumi — Kab. Bandung

Dashboard statis (React + Vite + Recharts). Data dari pipeline `example_scrap`.

## Update data
Di repo `example_scrap`: `./run_pipeline.sh` → salin `dashboard_data/*.json` ke `public/data/` di sini → commit.

## Dev
`npm install && npm run dev`

## Build & deploy
`DEPLOY_BASE=/nama-repo/ npm run build` → deploy folder `dist/` ke GitHub Pages / Netlify.

## Prinsip
Prediksi model ML selalu ditampilkan berpasangan baseline + label MAE — model
tidak mengalahkan baseline persistence di horizon manapun (lihat section Ringkasan Riset).
```

- [ ] **Step 3: (Optional) GitHub Pages workflow** `.github/workflows/deploy.yml`

```yaml
name: deploy
on: { push: { branches: [main] } }
permissions: { contents: read, pages: write, id-token: write }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: DEPLOY_BASE=/${{ github.event.repository.name }}/ npm run build
      - uses: actions/upload-pages-artifact@v3
        with: { path: dist }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: "${{ steps.deployment.outputs.page_url }}" }
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 4: Commit** — `git commit -am "chore: build config, README, deploy workflow"`

- [ ] **Step 5: Final check** — `npm test` all green, `npm run build` clean, deploy, open the live URL, click through all 6 sections + theme toggle + all 3 selectors.

---

## Self-Review

**Spec coverage:**
- PRD §5.1 Hero → Task 10 ✓ · §5.2 Eksplorasi → Task 9 ✓ · §5.3 Cuaca & Kurs → Tasks 7, 11 ✓ · §5.4 Prediksi → Task 13 ✓ · §5.5 Rekomendasi → Tasks 12, 14 ✓ · §5.6 Riset → Task 15 ✓
- PRD §6 non-fungsional: stack (Task 1), lazy fetch (Task 3), responsive + a11y (Task 16), theme (Task 4), deploy (Task 17) ✓
- PRD "prinsip wajib" (§2): paired predictions (Task 13 `PrediksiChip`), data-date banner (Task 5 shell + Task 13 `BannerKejujuran`), caveat marking (Task 9 `BadgeCaveat` + Task 13 empty-chip) ✓
- Design doc §3 chart palette → `tokens.js` (Task 1), consumed in every chart task ✓
- Design doc §5 signature → Task 10 `PitaKetidakpastian` ✓
- Design doc §6 hand-drawn texture → marked OPSIONAL in spec; not a task (acceptable — spec says skippable). If wanted, add as a follow-up.
- Design doc §9 per-chart Recharts mapping → Tasks 7, 9, 10, 11, 13, 14 ✓

**Placeholder scan:** Task 9 Step 1 and Task 9 Step 6 tell the implementer to hand-compute and adjust one expected assertion string — this is deliberate (the value depends on a rounding choice made in Step 3) and the how is fully specified. No "TODO"/"add error handling"/"similar to Task N" left.

**Type consistency:** `useData(file)` returns `{data, loading, error}` — used consistently. `getTokens`/`useTokens` keys (`ink, inkMuted, line, surface, bg, brand, signature, cat1, cat2, cat3, naik, turun, stabil, rain, temp`) match design doc §12 and all chart usages. `buildEnvelope` → `{min,max,avg}[]` used in Tasks 9, 10. `rekomendasiBand(b, harga, kondisi)` signature matches Task 12 def and Task 14 call. `PitaKetidakpastian` props (`data, kondisi, tinggi, lebaranX`) consistent Task 10 ↔ Task 14.

## Execution Handoff

Plan saved to `docs/dashboard-implementation-plan.md`. Copy it (+ PRD + design) into the new `dashboard-harga-sayur` repo's `docs/` before starting.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session with checkpoints.

Which approach?
