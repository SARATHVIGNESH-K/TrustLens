# TrustLens — Client

React + Tailwind dashboard for the TrustLens video authenticity analyzer.

## Design

- **Palette**: graphite base, warm paper text, scanner-teal for verified/neutral state, ink-red for flagged/suspicious findings, evidence-green for confirmed authentic.
- **Type**: Fraunces (display/headline), IBM Plex Sans (UI copy), IBM Plex Mono (all data: scores, timestamps, metadata).
- **Motif**: "evidence panel" — hairline-bordered panels with viewfinder corner brackets instead of rounded cards + drop shadows. The hero is a frame-by-frame filmstrip with a single scan-line sweep on load, not a gradient-hero-with-big-number.

## Structure

```
src/
  components/
    Navbar.jsx
    Hero.jsx                 — filmstrip + scan sweep
    UploadCard.jsx            — drag & drop, validation, mock progress
    StatCard.jsx
    AuthenticityGauge.jsx     — recharts radial gauge (fake probability)
    SuspiciousTimeline.jsx    — colored segment timeline with hover detail
    ReasonsList.jsx           — explainable AI reasons
    RecentReports.jsx
  context/
    ThemeContext.jsx          — dark/light toggle, persisted to localStorage
  pages/
    Dashboard.jsx             — assembles the above with mock data
    Placeholder.jsx           — stub for History / Admin / Login / Report detail
  App.jsx
  main.jsx
  index.css
```

Currently wired with **mock data** (`Dashboard.jsx`) so the UI is fully explorable
before the backend exists. Swap the mock arrays for `axios` calls to
`/api/upload`, `/api/analyze`, `/api/report/{id}`, `/api/history`, `/api/stats`
once the FastAPI backend is running.

## Run locally

```bash
npm install
npm run dev
```

Requires network access to the npm registry and Google Fonts (Fraunces, IBM
Plex Sans, IBM Plex Mono) — both loaded via `index.html`.

## Not yet implemented (stubbed as Placeholder pages)

- `/history` — searchable list of past analyses
- `/admin` — system stats, model performance, logs
- `/login` — JWT auth form
- `/report/:id` — full report detail (heatmap overlay, forensic evidence, PDF export)

These are next once the backend contract (endpoints listed above) is in place.
