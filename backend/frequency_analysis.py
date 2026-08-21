"""
Frequency-Domain Analysis Module (Placeholder)
==============================================

PURPOSE (to be implemented next):
    Apply a Fourier transform to the image and look for periodic artefacts
    that diffusion-based generators leave in the high-frequency band. Real
    photos have a smooth, naturally-decaying frequency spectrum; AI images
    often have an abnormal spike or grid-like pattern in the high-frequency
    region caused by the upsampling / transpose-conv layers.

CONTRACT (already finalized so main.py can wire to it):
    analyze_frequency(image_path: str) -> dict
        Returns a dict with:
            - "score": float in [0, 1]
                0 = spectrum looks like a natural photo,
                1 = strong periodic / high-frequency anomaly typical of AI.
            - "signals": list[str]
                Human-readable detected anomalies.
            - "spectrum_path": str | None
                Optional path to a saved FFT magnitude visualization
                (useful as a second explainability image, like Grad-CAM).

This file currently returns a clearly-marked PLACEHOLDER result so the
backend endpoints work end-to-end. Replace `analyze_frequency` with the
real implementation when you build this module.
"""

from __future__ import annotations

from typing import Any, Dict


def analyze_frequency(image_path: str) -> Dict[str, Any]:
    """
    Placeholder frequency-domain analyzer.

    Real implementation should:
      1. Load the image as grayscale (or per-channel) numpy array.
      2. Compute the 2D FFT and shift zero-frequency to the centre.
      3. Convert magnitude to log scale for visualization.
      4. Detect a high-frequency peak or radial asymmetry, and score it.

    Args:
        image_path: filesystem path to the uploaded image.

    Returns:
        dict with keys: "score" (float), "signals" (list[str]),
        "spectrum_path" (str | None).
    """
    return {
        "score": 0.0,
        "signals": ["frequency_analysis: not yet implemented (placeholder)"],
        "spectrum_path": None,
    }
