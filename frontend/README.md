# Frontend — Cooling Scenario Simulator Dashboard

Interactive web dashboard for the Urban Heat AI system.

## Files

| File | Description |
|------|-------------|
| `index.html` | Dashboard layout with KPI cards, charts, sliders, and tables |
| `index.css` | Premium dark glassmorphism design with micro-animations |
| `app.js` | Chart.js visualizations, API calls, and slider logic |

## Features

- **7 intervention sliders** across 4 categories (Green/White/Blue/Grey)
- **Real-time predictions** using the trained GradientBoosting model
- **Before/After KPI cards** with animated value transitions
- **Heat Class Distribution** bar chart (Before vs After)
- **Feature Changes** horizontal bar chart showing % change per feature
- **Class Transition** bars (Low → Moderate → High → Extreme)
- **Detailed Feature Impact** table with per-feature before/after values

## Usage

The dashboard is served by the Flask backend (`backend/app.py`):

```bash
python backend/app.py
# Open http://localhost:5000
```

## Tech Stack

- **HTML5** + **Vanilla CSS** + **Vanilla JavaScript**
- **Chart.js 4.4.0** (CDN) for charts
- **Inter** + **JetBrains Mono** fonts (Google Fonts)
- No build tools or bundlers required
