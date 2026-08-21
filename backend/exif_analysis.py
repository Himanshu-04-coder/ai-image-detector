"""
EXIF Metadata Analysis Module (Placeholder)
============================================

PURPOSE (to be implemented next):
    Inspect the image's EXIF metadata for forensic signals that distinguish
    AI-generated images from real camera photos. Typical signals include:
      - Absence of camera make/model/EXIF tags (very common in AI images,
        since most diffusion models strip metadata by default)
      - Presence of diffusion-tool signatures (e.g. "Software: NovelAI",
        "stable-diffusion", "ComfyUI", etc.)
      - Suspiciously uniform DateTime fields
      - Missing GPS / lens info

CONTRACT (already finalized so main.py can wire to it):
    analyze_exif(image_path: str) -> dict
        Returns a dict with:
            - "score": float in [0, 1]
                How much the EXIF data looks AI-like. 0 = looks real,
                1 = strongly suggests AI generation.
            - "signals": list[str]
                Human-readable list of detected signals (used in viva /
                shown to the user as explanation).
            - "raw_metadata": dict
                Selected EXIF fields for transparency. Empty if the image
                has no EXIF.

This file currently returns a clearly-marked PLACEHOLDER result so the
backend endpoints work end-to-end. Replace `analyze_exif` with the real
implementation when you build this module.
"""

from __future__ import annotations

from typing import Any, Dict


def analyze_exif(image_path: str) -> Dict[str, Any]:
    """
    Placeholder EXIF analyzer.

    Real implementation should:
      1. Open the image with Pillow and read `image.getexif()`.
      2. Look for known diffusion-tool signatures in the "Software" tag.
      3. Score the image based on which tags are missing vs present
         compared to a typical real-camera EXIF profile.
      4. Return the score, human-readable signals, and raw metadata.

    Args:
        image_path: filesystem path to the uploaded image.

    Returns:
        dict with keys: "score" (float), "signals" (list[str]),
        "raw_metadata" (dict).
    """
    return {
        "score": 0.0,
        "signals": ["exif_analysis: not yet implemented (placeholder)"],
        "raw_metadata": {},
    }
