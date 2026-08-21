"""
main.py - FastAPI entry point for the AI Image Detector backend
================================================================

ENDPOINTS:
    POST /predict         - single image inference + Grad-CAM + DB log
    POST /predict-batch   - same, for many images
    GET  /history         - last 50 scans from SQLite, newest first
    GET  /stats           - model evaluation metrics from metrics.json
    POST /predict-detailed - /predict + EXIF + frequency, with combined verdict

WHY EACH PIECE EXISTS:
    - CORS middleware: lets the React dev server (localhost:3000 or :5173)
      call this API during development. In production the frontend would
      be served from the same origin and CORS wouldn't be needed.
    - StaticFiles mount: lets the frontend <img src="/static/uploads/...">
      directly to view uploaded images and Grad-CAM overlays without
      needing a separate file server.
    - Lifespan context (`@asynccontextmanager`): the modern FastAPI
      replacement for the old `@app.on_event("startup")` decorator.
      We load the heavy model here so the first request is fast.
    - Custom exception handlers: convert Python errors into clean JSON
      responses (FastAPI's default HTML error page is awful for an API).
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import exif_analysis
import frequency_analysis
import model_utils
from database import Scan, get_db, init_db
from schemas import (
    CNNResult,
    CombinedVerdict,
    DetailedPredictResponse,
    EXIFResult,
    FrequencyResult,
    HistoryResponse,
    PredictResponse,
    StatsResponse,
)

# ---------------------------------------------------------------
# Logging
# ---------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai-image-detector")

# ---------------------------------------------------------------
# Allowed upload content types
# ---------------------------------------------------------------
# Browsers send slightly different MIME types for the same format
# (e.g. "image/jpeg" vs "image/jpg"), so we match loosely.
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB cap to avoid OOMing on huge images


# ---------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan hook. Runs once at startup, once at shutdown.

    Startup: load the model into memory and create the DB tables.
    Both are idempotent - safe to call if already done.
    """
    logger.info("Starting up - loading model + initialising database...")
    try:
        model_utils.load_model_once()
        logger.info("Model loaded successfully on device %s", model_utils.get_device())
    except FileNotFoundError as exc:
        # Don't crash the server - let /predict return a clear 500 instead.
        logger.error("Model failed to load: %s", exc)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected error loading model: %s", exc)

    init_db()
    logger.info("Database initialised.")

    yield  # <-- the app runs here

    logger.info("Shutting down.")


# ---------------------------------------------------------------
# App factory
# ---------------------------------------------------------------
app = FastAPI(
    title="AI Image Detector API",
    description=(
        "Detects whether an image is REAL or AI-GENERATED using a ResNet50 "
        "binary classifier trained on CIFAKE. Endpoints include single & "
        "batch prediction, Grad-CAM explainability, EXIF & frequency "
        "forensic analysis, and a scan history backed by SQLite."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------
# CORS - allow local frontend dev servers
# ---------------------------------------------------------------
# React (CRA / Next) defaults to :3000; Vite defaults to :5173.
# We list both explicitly rather than using "*" so credentials could be
# added later without breaking the browser's same-origin rules.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------
# Static files (uploads + heatmaps)
# ---------------------------------------------------------------
# Anything under backend/static/ is served at /static/...
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(os.path.join(STATIC_DIR, "uploads"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "heatmaps"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------
# Custom exception handlers - clean JSON errors for an API
# ---------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Wrap FastAPI's HTTPException in a consistent JSON envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for unexpected errors. Logs the traceback and returns a
    generic 500 - never leak internals to the client.
    """
    logger.exception("Unhandled exception while handling %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500},
    )


# ---------------------------------------------------------------
# File validation helper
# ---------------------------------------------------------------
async def _read_and_validate_upload(file: UploadFile) -> bytes:
    """
    Read the upload to memory, enforcing size + content-type checks.

    Why read eagerly?
        UploadFile.file is a SpooledTemporaryFile - reading it once
        gives us a bytes object we own, free of FastAPI's internal
        cleanup rules.

    Raises HTTPException(400/413/415) with descriptive messages.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type: {file.content_type!r}. "
                f"Allowed: {sorted(ALLOWED_CONTENT_TYPES)}"
            ),
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File too large ({len(contents)} bytes). "
                f"Max allowed: {MAX_UPLOAD_BYTES} bytes."
            ),
        )

    return contents


# ---------------------------------------------------------------
# Health check
# ---------------------------------------------------------------
@app.get("/", tags=["health"])
async def root():
    """Cheap health check - confirms the server is up."""
    return {"status": "ok", "service": "ai-image-detector"}


# ---------------------------------------------------------------
# 1. POST /predict
# ---------------------------------------------------------------
@app.post(
    "/predict",
    response_model=PredictResponse,
    tags=["inference"],
    summary="Classify a single image and produce a Grad-CAM heatmap.",
)
async def predict(file: UploadFile = File(...)):
    """
    Accepts a single image upload, runs the ResNet50 binary classifier,
    saves the image + heatmap under /static, logs the scan to SQLite,
    and returns the prediction.

    Errors:
        415 - wrong content type
        400 - empty / corrupt image
        413 - file exceeds 20MB
        500 - model not loaded or unexpected failure
    """
    contents = await _read_and_validate_upload(file)
    try:
        result = model_utils.process_image(contents, file.filename or "upload.jpg")
    except ValueError as exc:
        # Corrupted image / PIL couldn't decode it
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Inference failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inference failed. See server logs.",
        ) from exc
    return result


# ---------------------------------------------------------------
# 2. POST /predict-batch
# ---------------------------------------------------------------
@app.post(
    "/predict-batch",
    response_model=List[PredictResponse],
    tags=["inference"],
    summary="Classify multiple images in one request.",
)
async def predict_batch(files: List[UploadFile] = File(...)):
    """
    Same as /predict, but for many files. We process them sequentially
    (rather than batching tensors) because Grad-CAM needs a per-image
    backward pass anyway, so GPU batching wouldn't help here.

    A failure on one image doesn't stop the others - we return a
    per-image error in place of the result so the frontend can show
    which uploads failed.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided.",
        )

    results: List[dict] = []
    for f in files:
        try:
            contents = await _read_and_validate_upload(f)
            results.append(model_utils.process_image(contents, f.filename or "upload.jpg"))
        except HTTPException as exc:
            # Per-file validation error - record it and continue.
            results.append({"error": exc.detail, "filename": f.filename})
        except ValueError as exc:
            results.append({"error": str(exc), "filename": f.filename})
        except Exception as exc:
            logger.exception("Batch item failed (%s): %s", f.filename, exc)
            results.append({"error": "inference failed", "filename": f.filename})

    return results


# ---------------------------------------------------------------
# 3. GET /history
# ---------------------------------------------------------------
@app.get(
    "/history",
    response_model=HistoryResponse,
    tags=["history"],
    summary="Return the 50 most recent scans.",
)
async def history(db: Session = Depends(get_db)):
    """
    Read-only listing from the SQLite scans table. Ordered by id DESC
    so newest is first - the table has a primary-key index, so this is
    the cheapest ordering.

    Note: id DESC and timestamp DESC give the same order here because
    ids are assigned by SQLite in insertion order, but we use id to
    avoid relying on clock skew between insert time and row creation.
    """
    scans = db.query(Scan).order_by(Scan.id.desc()).limit(50).all()
    return scans


# ---------------------------------------------------------------
# 4. GET /stats
# ---------------------------------------------------------------
def _load_metrics_file() -> dict:
    """
    Try multiple candidate paths for the metrics file so the backend
    works whether the user drops metrics.json into backend/ or the
    project root. Returns parsed dict, or raises FileNotFoundError.
    """
    BASE = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(BASE, "metrics.json"),
        os.path.join(BASE, "test_metrics.json"),
        os.path.join(BASE, "training_history.json"),
        os.path.join(BASE, "..", "model_training", "test_metrics.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r") as f:
                return json.load(f), path
    raise FileNotFoundError(
        "Could not find metrics.json / training_history.json. "
        "Place one in the backend/ folder."
    )


@app.get(
    "/stats",
    response_model=StatsResponse,
    tags=["stats"],
    summary="Saved model evaluation metrics.",
)
async def stats():
    """
    Read metrics from disk on every call. The file is tiny, so caching
    isn't worth the invalidation complexity during a viva demo.

    Field mapping (we accept several naming conventions so users can
    drop in either test_metrics.json or a custom metrics.json):
        accuracy   <- "accuracy"
        precision  <- "precision" or "precision_score"
        recall     <- "recall" or "recall_score"
        f1         <- "f1" or "f1_score"
        confusion  <- "confusion_matrix" (default 2x2 zero matrix if missing)
    """
    try:
        metrics, source_path = _load_metrics_file()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    def _g(*keys, default=None):
        """Look up the first present key in `metrics`."""
        for k in keys:
            if k in metrics:
                return metrics[k]
        return default

    return StatsResponse(
        accuracy=_g("accuracy", default=0.0),
        precision=_g("precision", "precision_score", default=0.0),
        recall=_g("recall", "recall_score", default=0.0),
        f1=_g("f1", "f1_score", "f1-score", default=0.0),
        confusion_matrix=_g("confusion_matrix", default=[[0, 0], [0, 0]]),
    )


# ---------------------------------------------------------------
# 5. POST /predict-detailed
# ---------------------------------------------------------------
def _combine_verdict(
    cnn_label: str,
    cnn_confidence: float,
    exif_score: float,
    frequency_score: float,
) -> CombinedVerdict:
    """
    Aggregate the three signals into one final verdict.

    Scoring rule (deliberately simple and explainable for viva):
        - cnn_score        = P(AI-GENERATED) from the CNN. If the CNN says
                             REAL we use (1 - confidence); if it says
                             AI-GENERATED we use confidence directly.
        - exif_score       = 0..1, AI-likelihood from metadata.
        - frequency_score  = 0..1, AI-likelihood from FFT.

        Combined AI-likelihood =
            0.6 * cnn_score  +  0.25 * exif_score  +  0.15 * frequency_score

        (CNN gets the highest weight because it's the only signal that
         actually learned from labelled data. The other two are forensic
         hints that the user said will be implemented later.)

    Threshold: >= 0.5 -> "AI-GENERATED", else "REAL".
    """
    cnn_ai_prob = cnn_confidence if cnn_label == "AI-GENERATED" else (1.0 - cnn_confidence)
    combined_ai_prob = (
        0.6 * cnn_ai_prob + 0.25 * exif_score + 0.15 * frequency_score
    )
    combined_ai_prob = max(0.0, min(1.0, combined_ai_prob))

    final_label = "AI-GENERATED" if combined_ai_prob >= 0.5 else "REAL"
    # Confidence = how sure we are of the final label (distance from threshold)
    final_confidence = (
        combined_ai_prob if final_label == "AI-GENERATED" else (1.0 - combined_ai_prob)
    )

    rationale = (
        f"CNN P(AI)={cnn_ai_prob:.2f} (weight 0.60), "
        f"EXIF score={exif_score:.2f} (weight 0.25), "
        f"frequency score={frequency_score:.2f} (weight 0.15). "
        f"Combined P(AI)={combined_ai_prob:.2f}."
    )
    return CombinedVerdict(
        label=final_label,
        confidence=float(final_confidence),
        rationale=rationale,
    )


@app.post(
    "/predict-detailed",
    response_model=DetailedPredictResponse,
    tags=["inference"],
    summary="CNN + EXIF + frequency analysis with combined verdict.",
)
async def predict_detailed(file: UploadFile = File(...)):
    """
    Like /predict, but also runs EXIF and frequency forensic modules
    and combines all three signals into a final verdict.

    The forensic modules are currently placeholders that return 0.0 -
    see exif_analysis.py and frequency_analysis.py. Once you implement
    them, this endpoint automatically picks up the real scores.
    """
    contents = await _read_and_validate_upload(file)

    # ---- CNN branch (same as /predict) ----
    try:
        cnn_result_dict = model_utils.process_image(contents, file.filename or "upload.jpg")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Detailed inference failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inference failed. See server logs.",
        ) from exc

    cnn_result = CNNResult(
        label=cnn_result_dict["label"],
        confidence=cnn_result_dict["confidence"],
        heatmap_url=cnn_result_dict["heatmap_url"],
    )

    # ---- Forensic branches ----
    # `process_image` returns the on-disk path of the saved upload so
    # we can run forensic analysis on the exact bytes the CNN saw.
    image_path = cnn_result_dict.get("saved_path")
    if not image_path or not os.path.isfile(image_path):
        raise HTTPException(
            status_code=500,
            detail="Could not locate saved image for forensic analysis.",
        )

    exif_dict = exif_analysis.analyze_exif(image_path)
    freq_dict = frequency_analysis.analyze_frequency(image_path)

    exif_result = EXIFResult(
        score=float(exif_dict.get("score", 0.0)),
        signals=list(exif_dict.get("signals", [])),
        raw_metadata=dict(exif_dict.get("raw_metadata", {})),
    )
    frequency_result = FrequencyResult(
        score=float(freq_dict.get("score", 0.0)),
        signals=list(freq_dict.get("signals", [])),
        spectrum_path=freq_dict.get("spectrum_path"),
    )

    combined_verdict = _combine_verdict(
        cnn_label=cnn_result.label,
        cnn_confidence=cnn_result.confidence,
        exif_score=exif_result.score,
        frequency_score=frequency_result.score,
    )

    return DetailedPredictResponse(
        cnn_result=cnn_result,
        exif_result=exif_result,
        frequency_result=frequency_result,
        combined_verdict=combined_verdict,
    )
