"""
model_utils.py - Model loading, inference, Grad-CAM, and DB logging
==================================================================

This is the core "brain" of the backend. It does four things:

1. `load_model_once()` - builds the ResNet50 architecture, loads the
   saved weights from disk, puts it in eval mode, and stashes it on
   a module-level singleton so it's only loaded ONCE per server
   process (loading a 90MB model on every request would be slow).

2. `run_inference()` - takes a saved image path, runs a forward
   pass, returns the predicted class index and confidence.

3. `run_gradcam()` - thin wrapper that calls generate_gradcam()
   from grad_cam.py and translates the output path to a URL the
   frontend can hit.

4. `process_image()` - the end-to-end pipeline used by /predict:
   save the upload, run inference, generate a heatmap, write a
   row to the SQLite scans table, return everything as a dict
   matching schemas.PredictResponse.

WHY A SEPARATE MODULE?
    Keeping model logic out of main.py means main.py just describes
    routes. The actual heavy lifting is testable in isolation, and
    the same code can be reused from a notebook for sanity checks.
"""

from __future__ import annotations

import io
import os
import uuid
from datetime import datetime
from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, UnidentifiedImageError
from torchvision import transforms

from grad_cam import CLASS_NAMES, generate_gradcam, load_model
from database import Scan, SessionLocal

# ---------------------------------------------------------------
# Constants
# ---------------------------------------------------------------
# MUST match the values used in training (grad_cam.py). If these drift
# the model will still return numbers but they will be meaningless.
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
IMG_SIZE = 64

# Where uploaded images and generated heatmaps are stored. These are
# served as static files by FastAPI (see main.py).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
HEATMAP_DIR = os.path.join(BASE_DIR, "static", "heatmaps")

# Map internal class index -> the string the frontend displays.
# Index 0 in training was "FAKE"; we rename it to "AI-GENERATED" for
# the UI (the trained model never sees the renamed label - it's just
# a presentation choice).
LABEL_DISPLAY = {
    0: "AI-GENERATED",
    1: "REAL",
}


# ---------------------------------------------------------------
# Preprocessing (mirrors grad_cam.py so we don't depend on its
# private `inference_transform`).
# ---------------------------------------------------------------
_preprocess = transforms.Compose(
    [
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ]
)


# ---------------------------------------------------------------
# Module-level singletons (loaded once at startup, reused per request)
# ---------------------------------------------------------------
_model: Optional[torch.nn.Module] = None
_device: Optional[torch.device] = None


def _resolve_model_path() -> str:
    """
    Locate the trained weights file.

    Search order:
      1. env var AI_DETECTOR_MODEL_PATH (lets ops override without code changes)
      2. backend/model/best_model.pth (the canonical backend location)
      3. ../model_training/best_model.pth (the original training output,
         kept as a fallback in case the backend copy isn't present)

    Raises FileNotFoundError with a helpful message if none exist.
    """
    candidates = [
        os.environ.get("AI_DETECTOR_MODEL_PATH"),
        os.path.join(BASE_DIR, "model", "best_model.pth"),
        os.path.join(BASE_DIR, "..", "model_training", "best_model.pth"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return os.path.abspath(path)
    raise FileNotFoundError(
        "Could not find best_model.pth. Looked in: "
        + ", ".join(p for p in candidates if p)
    )


def load_model_once() -> torch.nn.Module:
    """
    Load the trained ResNet50 exactly once. Subsequent calls return
    the cached model.

    Why "once"?
        - ResNet50 weights are ~90MB; loading them per request would
          saturate disk I/O and add ~1-2s latency to every /predict.
        - The model is read-only at inference time, so multiple
          threads/processes can safely share one copy in memory.

    Returns the loaded model (also stored as a module global).
    """
    global _model, _device
    if _model is not None:
        return _model

    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_path = _resolve_model_path()
    # grad_cam.load_model() already does the ResNet50 rebuild + state_dict load.
    _model = load_model(model_path, _device)
    return _model


def get_device() -> torch.device:
    """Convenience accessor - guarantees device is initialised."""
    if _device is None:
        load_model_once()
    assert _device is not None
    return _device


# ---------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------
def _load_image_or_raise(image_path: str) -> Image.Image:
    """
    Open an image as RGB. Raises ValueError with a clean message if
    the file isn't a real image (PIL raises UnidentifiedImageError
    for most corruptions, and the caller converts to 400/422).
    """
    try:
        return Image.open(image_path).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Could not decode image: {exc}") from exc


def run_inference(image_path: str) -> Tuple[int, float, float]:
    """
    Run a single forward pass.

    Returns:
        pred_idx: int (0 = FAKE/AI-GENERATED, 1 = REAL - same as CLASS_NAMES)
        confidence: float in [0,1] for the predicted class
        fake_prob: float in [0,1] - convenience value, probability the
                   image is FAKE/AI-generated, regardless of prediction.
                   Useful for downstream confidence weighting.
    """
    model = load_model_once()
    device = get_device()

    img = _load_image_or_raise(image_path)
    tensor = _preprocess(img).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs = F.softmax(logits, dim=1)[0].cpu().numpy()

    pred_idx = int(np.argmax(probs))
    return pred_idx, float(probs[pred_idx]), float(probs[0])


def run_gradcam(image_path: str, output_path: str) -> None:
    """
    Thin wrapper around grad_cam.generate_gradcam() that just swallows
    the verbose stdout and ensures the output directory exists.

    Raises any exception from grad_cam - we let the endpoint decide
    the HTTP status code.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    model = load_model_once()
    generate_gradcam(image_path, model, output_path, device=get_device())


# ---------------------------------------------------------------
# End-to-end pipeline used by /predict
# ---------------------------------------------------------------
def _safe_extension(filename: str) -> str:
    """
    Return a lowercased file extension with a leading dot, defaulting
    to '.jpg' if the filename doesn't have one. We don't trust the
    extension for content validation - that's done elsewhere - but we
    do use it to keep saved files self-describing.
    """
    _, ext = os.path.splitext(filename)
    return ext.lower() if ext else ".jpg"


def _save_upload(file_bytes: bytes, original_filename: str) -> Tuple[str, str]:
    """
    Write the uploaded bytes to UPLOAD_DIR under a UUID-prefixed name.

    Returns (absolute path the model will read, relative URL the
    frontend can <img src=...>). We use a UUID so two uploads with
    the same filename don't collide.

    Why bytes in -> path out?
        FastAPI gives us UploadFile.file which is a SpooledTemporaryFile.
        Reading it to bytes once means we own the file's location and
        lifetime, instead of depending on FastAPI's internal cleanup.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = _safe_extension(original_filename)
    unique = f"{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(UPLOAD_DIR, unique)
    with open(abs_path, "wb") as f:
        f.write(file_bytes)
    rel_url = f"/static/uploads/{unique}"
    return abs_path, rel_url


def _record_scan(filename: str, label: str, confidence: float, thumbnail_url: str) -> None:
    """
    Insert one row into the scans table.

    We open a fresh SessionLocal here (rather than receiving one from
    a dependency) because the inference helpers in this file are also
    used from contexts without a request-scoped DB session (e.g. a
    future CLI / sanity-check script).
    """
    db = SessionLocal()
    try:
        scan = Scan(
            filename=filename,
            label=label,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            thumbnail_path=thumbnail_url,
        )
        db.add(scan)
        db.commit()
    finally:
        db.close()


def process_image(file_bytes: bytes, original_filename: str) -> dict:
    """
    Full /predict pipeline for a single uploaded image.

    Steps:
      1. Save the upload to disk.
      2. Run inference (single forward pass).
      3. Run Grad-CAM to produce an explainability overlay.
      4. Persist a scan record to the database.
      5. Return a dict matching schemas.PredictResponse.

    Raises:
        ValueError - if the image can't be decoded.
        RuntimeError - if anything else (model load, disk write, etc.)
                       fails. Callers should map these to 500.
    """
    # ---- 1. Save upload ----
    abs_image_path, image_url = _save_upload(file_bytes, original_filename)

    # ---- 2. Inference ----
    pred_idx, confidence, _fake_prob = run_inference(abs_image_path)
    label = LABEL_DISPLAY[pred_idx]

    # ---- 3. Grad-CAM ----
    heatmap_filename = f"{os.path.splitext(os.path.basename(abs_image_path))[0]}_heatmap.png"
    heatmap_abs = os.path.join(HEATMAP_DIR, heatmap_filename)
    run_gradcam(abs_image_path, heatmap_abs)
    heatmap_url = f"/static/heatmaps/{heatmap_filename}"

    # ---- 4. Persist ----
    _record_scan(original_filename, label, confidence, image_url)

    # ---- 5. Return ----
    # `saved_path` is included for downstream consumers (e.g.
    # /predict-detailed needs it to run EXIF/frequency analysis on the
    # same file). It's not in the public Pydantic schema - endpoints
    # that want it can pull it from the dict, others ignore it.
    return {
        "label": label,
        "confidence": confidence,
        "heatmap_url": heatmap_url,
        "saved_path": abs_image_path,
    }
