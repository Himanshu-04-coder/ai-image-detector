"""
schemas.py - Pydantic response/request models
=============================================

WHY PYDANTIC?
    Pydantic gives us automatic JSON validation and self-documenting
    API schemas. FastAPI uses these classes to:
      - validate incoming request bodies / query params
      - serialize outgoing responses
      - generate the OpenAPI / Swagger UI documentation at /docs

VIVA NOTE:
    These are *response* shapes for the frontend. Field names use
    snake_case in Python, and FastAPI auto-converts them to camelCase
    or whatever JSON convention the frontend prefers. We keep them
    snake_case here for clarity and consistency with the DB layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------
# /predict and /predict-batch responses
# ---------------------------------------------------------------
class PredictResponse(BaseModel):
    """Single-image prediction result returned to the frontend."""

    label: str = Field(
        ...,
        description='"REAL" if the model thinks the image is a real '
        'photo, "AI-GENERATED" otherwise.',
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Softmax probability the model assigned to the predicted class.",
    )
    heatmap_url: str = Field(
        ...,
        description="Relative URL to the Grad-CAM overlay image "
        "(served by FastAPI's StaticFiles mount on /static).",
    )


# A batch response is just a list of the same shape - typed explicitly
# so it shows up nicely in the Swagger UI.
PredictBatchResponse = List[PredictResponse]


# ---------------------------------------------------------------
# /history responses
# ---------------------------------------------------------------
class HistoryItem(BaseModel):
    """One row from the SQLite scans table, formatted for the frontend."""

    id: int
    filename: str
    label: str
    confidence: float
    timestamp: datetime
    thumbnail_path: str = Field(
        ...,
        description="Path the frontend can pass to <img src=...> to show "
        "the uploaded image (served from /static/uploads).",
    )


HistoryResponse = List[HistoryItem]


# ---------------------------------------------------------------
# /stats response
# ---------------------------------------------------------------
class StatsResponse(BaseModel):
    """
    Saved model evaluation metrics, loaded from metrics.json /
    training_history.json at request time.

    Confusion matrix is a 2x2 nested list:
        [[TN, FP],
         [FN, TP]]
    where rows = actual class, cols = predicted class.
    """

    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: List[List[int]]


# ---------------------------------------------------------------
# /predict-detailed response
# ---------------------------------------------------------------
class CNNResult(BaseModel):
    """Same shape as PredictResponse - the model's verdict + heatmap."""

    label: str
    confidence: float
    heatmap_url: str


class EXIFResult(BaseModel):
    """
    Output of exif_analysis.analyze_exif().

    NOTE: ``risk_score`` is a HEURISTIC supporting signal - it must
    never be used as a standalone detector. See the long docstring
    at the top of ``exif_analysis.py`` for the honest limitations.
    """

    has_exif: bool = Field(
        ...,
        description="True if the image contained an EXIF block at all.",
    )
    camera_make: Optional[str] = Field(
        None,
        description='Value of the "Make" EXIF tag (camera manufacturer), if present.',
    )
    camera_model: Optional[str] = Field(
        None,
        description='Value of the "Model" EXIF tag (camera model), if present.',
    )
    software: Optional[str] = Field(
        None,
        description='Value of the "Software" EXIF tag, if present.',
    )
    risk_score: str = Field(
        ...,
        description='Discrete AI-likelihood rating: "Low" | "Medium" | "High".',
    )
    risk_reasons: List[str] = Field(
        ...,
        description="Human-readable list of EXIF red flags (or a reassuring note "
        "if none were found).",
    )


class FrequencyResult(BaseModel):
    """
    Output of frequency_analysis.analyze_frequency().

    NOTE: the ``high_freq_energy_ratio`` is a single classical
    signal-processing feature, NOT a learned AI-likelihood. It is
    included as a supporting visual + statistical signal only.
    See the long docstring at the top of ``frequency_analysis.py``
    for the honest limitations and how to talk about them in viva.
    """

    spectrum_image_path: Optional[str] = Field(
        None,
        description="Filesystem path (or URL) of the saved FFT spectrum "
        "visualization PNG.",
    )
    high_freq_energy_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of high-frequency energy to total energy in the "
        "FFT magnitude spectrum. Higher values can correlate with "
        "diffusion upsampling artefacts but are also elevated in "
        "busy-textured real photos.",
    )
    note: str = Field(
        ...,
        description="Honest reminder that this is a heuristic supporting "
        "signal, not a standalone classifier.",
    )


class CombinedVerdict(BaseModel):
    """
    Final aggregated decision across all three signals.

    `label` mirrors the same vocabulary as the CNN result so the
    frontend can render it with the same UI component.
    """

    label: str = Field(..., description='"REAL" or "AI-GENERATED".')
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(
        ...,
        description="Human-readable explanation of how the three signals were combined.",
    )


class DetailedPredictResponse(BaseModel):
    """Combined response for /predict-detailed."""

    cnn_result: CNNResult
    exif_result: EXIFResult
    frequency_result: FrequencyResult
    combined_verdict: CombinedVerdict
