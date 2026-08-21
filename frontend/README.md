# DeepGuard — Frontend

React + Vite + Tailwind CSS dashboard for the **AI Image Detector** FastAPI
backend.

## Stack

- **Vite** + **React 19**
- **Tailwind CSS 3** (with `darkMode: 'class'`)
- **React Router 7** for routing
- **Axios** for API calls
- **Lucide** icons
- **Recharts** (used for the confusion-matrix chart)

## Folder layout

```
src/
├── api/
│   └── client.js          # axios instance + endpoint wrappers
├── components/            # shared UI: Sidebar, VerdictBadge, StatCard, …
│   ├── Sidebar.jsx
│   ├── MobileHeader.jsx
│   ├── VerdictBadge.jsx
│   ├── StatCard.jsx
│   ├── Spinner.jsx
│   ├── DropZone.jsx
│   ├── Accordion.jsx
│   └── PageHeader.jsx
├── lib/
│   └── utils.js           # classnames helper + formatters
├── pages/
│   ├── HomePage.jsx       # "/" — single-image detailed analysis
│   ├── BatchPage.jsx      # "/batch" — multi-file
│   ├── HistoryPage.jsx    # "/history" — sortable table
│   └── StatsPage.jsx      # "/stats" — KPI cards + confusion matrix
├── App.jsx                # layout shell (sidebar + outlet)
├── main.jsx               # router
└── index.css              # Tailwind layers + base styles
```

## Configuration

Copy `.env.example` to `.env` and set the backend URL:

```bash
cp .env.example .env
```

```dotenv
VITE_API_URL=http://localhost:8000
```

The Axios client reads `VITE_API_URL` at build time. Change it (and rebuild)
to point at a hosted backend.

## Running

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # production bundle in dist/
npm run preview    # serve the production bundle locally
```

The FastAPI backend must be reachable on the URL in `VITE_API_URL` for the
pages to return data.

## Pages

| Path        | Backend call        | What it shows                                    |
| ----------- | ------------------- | ------------------------------------------------ |
| `/`         | `POST /predict-detailed` | Original image, verdict badge, Grad-CAM, EXIF + FFT |
| `/batch`    | `POST /predict-batch`    | Multi-file queue + table of verdicts             |
| `/history`  | `GET /history`           | Sortable table of past predictions              |
| `/stats`    | `GET /stats`             | Accuracy / precision / recall / F1 + confusion matrix |

## Design notes

- Sidebar nav on `lg+`, bottom tab bar on mobile.
- Verdict badge color is consistent everywhere: emerald = **REAL**,
  red = **AI-GENERATED**, neutral for unknown.
- All asset URLs (heatmaps, frequency spectra, thumbnails) accept either
  a `data:` URL, a relative path under the backend, or a `{ url, b64 }`
  object — see `resolveAssetUrl` / `resolveThumbUrl` in the pages.
- The dashboard works in dark mode automatically via Tailwind's
  `dark:` variants (toggle your OS theme to preview).
