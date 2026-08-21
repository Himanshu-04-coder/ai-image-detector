# AI Image Detector — Backend

FastAPI server that wraps the trained ResNet50 model and exposes it as
a REST API for the React frontend.

## Endpoints

| Method | Path                  | Purpose                                       |
|--------|-----------------------|-----------------------------------------------|
| POST   | `/predict`            | Single image → `{label, confidence, heatmap_url}` |
| POST   | `/predict-batch`      | Many images → array of the same shape          |
| GET    | `/history`            | Last 50 scans from SQLite                      |
| GET    | `/stats`              | Model metrics loaded from `metrics.json`       |
| POST   | `/predict-detailed`   | CNN + EXIF + frequency + combined verdict      |

The auto-generated Swagger UI lives at `http://localhost:8000/docs`.

## Install

```powershell
cd backend
pip install -r requirements.txt
```

> **Windows / PowerShell note:** `pip install` puts executables like
> `uvicorn.exe` into
> `C:\Users\<you>\AppData\Roaming\Python\Python313\Scripts\`, which is
> **not** on the default `PATH`. That's why `uvicorn main:app --reload`
> fails with *"term 'uvicorn' is not recognized"*. Use `python -m`
> instead — it bypasses the PATH lookup entirely:

```powershell
python -m uvicorn main:app --reload
```

(If you prefer, add the Scripts dir above to your PATH and the bare
`uvicorn …` command will work too.)

## Run

```powershell
cd backend
python -m uvicorn main:app --reload
```

Then visit <http://localhost:8000/docs>.

## File layout

```
backend/
├── main.py              FastAPI app, all 5 endpoints, CORS, static files
├── model_utils.py       Model load-once + inference + Grad-CAM + DB log
├── database.py          SQLAlchemy engine, Scan model, get_db dependency
├── schemas.py           Pydantic response models
├── exif_analysis.py     Placeholder EXIF forensic module
├── frequency_analysis.py Placeholder FFT forensic module
├── grad_cam.py          (pre-existing — reused as-is)
├── requirements.txt
├── test_metrics.json    Used by /stats
├── model/best_model.pth Trained ResNet50 weights (loaded at startup)
└── static/
    ├── uploads/         Saved uploaded images (created on first run)
    └── heatmaps/        Saved Grad-CAM overlays (created on first run)
```

## Notes for the viva

- **Model is loaded once** at app startup, not per request (see the
  `_model` singleton in `model_utils.py`).
- **Static files** are mounted at `/static/...` so the frontend can
  `<img src="/static/uploads/abc.jpg">` directly.
- **CORS** is restricted to `localhost:3000` (CRA/Next) and
  `localhost:5173` (Vite).
- **Combined verdict** in `/predict-detailed` uses fixed weights
  `0.6·CNN + 0.25·EXIF + 0.15·FFT` and a `0.5` threshold — documented
  in the response's `rationale` field.
