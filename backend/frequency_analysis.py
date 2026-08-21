"""
Frequency-Domain Analysis Module
================================

WHAT THIS MODULE DOES
---------------------
Applies a classical signal-processing pipeline to the image:

    1. Load the image with OpenCV and convert to grayscale.
    2. Compute the 2D Fast Fourier Transform (FFT) of the image.
    3. Shift the zero-frequency component to the centre of the spectrum
       (so the "DC" component is in the middle and frequencies grow
       radially outward - this is the form you almost always see in
       textbooks and papers on image forensics).
    4. Convert the magnitude spectrum to a log scale (because raw FFT
       magnitudes span many orders of magnitude and the DC component
       would otherwise swamp everything else).
    5. Save a visualization of the spectrum as a PNG using matplotlib
       with a grayscale colormap.
    6. Compute one simple statistical feature:

           high_freq_energy_ratio = high_frequency_energy / total_energy

       where "high frequency" = the outer annulus of the spectrum
       (excluding the DC centre). This is a classic frequency-domain
       heuristic: GAN / diffusion-generated images often show
       unusually strong periodic artefacts in the high-frequency band
       because of the transposed-convolution / upsampling layers in
       the generator. Real camera photos tend to have a smooth,
       naturally-decaying spectrum with most energy in the low and
       mid frequencies.

====================================================================
!! IMPORTANT - CLASSICAL HEURISTIC, NOT A TRAINED CLASSIFIER !!
====================================================================
This is a hand-crafted signal-processing feature, NOT a learned
model. That has implications you should be honest about in your
project report and viva:

    * It cannot adapt. A new diffusion model that produces spectra
      that look "natural" will defeat this signal entirely. We are
      not learning what AI images look like - we are measuring one
      particular physical signature.
    * It is sensitive to image content, not just to image origin.
      A photograph of a brick wall or a striped shirt will have
      plenty of high-frequency energy too - because the SUBJECT is
      periodic, not because the image is AI. Real photos of busy
      scenes can look "AI-like" under this metric.
    * The threshold is arbitrary. We pick a cutoff ratio to separate
      "outer annulus" from "central low-frequency disk", but there
      is no theoretically correct value - it is a knob, not a fact.
    * JPEG re-encoding (which most upload pipelines do) attenuates
      the highest frequencies. A heavily compressed real photo can
      look smoother than a freshly exported AI image.

For these reasons this module is a SUPPORTING visual + statistical
signal only. It is useful for the viva as a *demonstration of
classical image-forensics understanding* - you can show the FFT
spectrum side-by-side with the Grad-CAM heatmap to discuss what
each tells you. But it is intentionally given the LOWEST weight
in the combined verdict (0.15 of the total), and the CNN carries
the actual classification decision (weight 0.60).

For your project report you can honestly say:

    "The frequency-domain analysis is a classical FFT-based
     heuristic. It does not learn from data - it measures the ratio
     of high-frequency energy to total energy in the magnitude
     spectrum, which is often (but not always) elevated in images
     produced by upsampling-based generators. We treat it as a
     supporting signal that contributes a small amount to the
     combined verdict and as a second explainability artifact (the
     saved spectrum image) shown alongside Grad-CAM in the UI.
     Its standalone reliability is limited and it is never used in
     isolation."

====================================================================
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

try:
    import cv2  # OpenCV - image IO + grayscale conversion
    import numpy as np
except ImportError as exc:  # pragma: no cover - both are in requirements.txt
    raise ImportError(
        "OpenCV (cv2) and numpy are required for frequency_analysis. "
        "Install with: pip install opencv-python-headless numpy"
    ) from exc

# matplotlib is only needed for saving the spectrum visualization.
# Imported lazily inside the function so that headless server installs
# without matplotlib (rare, but possible) still get import errors at
# use-time rather than at module-import time.

logger = logging.getLogger("ai-image-detector.frequency")


# ---------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------

# Fraction of the spectrum (by radius, measured from the centre) that
# counts as "high frequency". The annulus from INNER_RADIUS_FRACTION
# to OUTER_RADIUS_FRACTION of the half-spectrum radius is what we sum.
#
# Why these values?
#   * We exclude the innermost disk because the very-low-frequency
#     content is dominated by the average brightness / DC component
#     and large smooth gradients - those are NOT what we want to
#     measure for AI artefacts.
#   * We also exclude the outermost 5% of pixels because FFT edges
#     can be noisy on rectangular images and because JPEG compression
#     attenuates those bins disproportionately.
INNER_RADIUS_FRACTION = 0.25
OUTER_RADIUS_FRACTION = 0.95

# Neutral fallback ratio used when ANY part of the pipeline fails
# (image unreadable, matplotlib missing, output path not writable,
# numpy error on a weird image, ...). 0.20 sits inside the
# "looks smooth / natural" bucket of main._freq_ratio_to_score, so a
# missing frequency signal does NOT push the combined verdict toward
# "AI-GENERATED" by itself. The endpoint can still return 200 and the
# CNN + EXIF signals are unaffected.
FALLBACK_RATIO_ON_ERROR = 0.20

# Standard caveat sentence we attach to every successful return as
# well, so the response always carries the honest "this is just a
# heuristic" reminder.
STANDARD_HEURISTIC_NOTE = (
    "Heuristic supporting signal, not a standalone classifier. "
    "The high-frequency energy ratio is a single statistical feature "
    "computed from the FFT magnitude spectrum; it is sensitive to "
    "image content as well as image origin and must be combined with "
    "the CNN prediction and EXIF signals to draw any reliable "
    "conclusion."
)


# ---------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------

# Fraction of the spectrum (by radius, measured from the centre) that
# counts as "high frequency". The annulus from INNER_RADIUS_FRACTION
# to OUTER_RADIUS_FRACTION of the half-spectrum radius is what we sum.
#
# Why these values?
#   * We exclude the innermost disk because the very-low-frequency
#     content is dominated by the average brightness / DC component
#     and large smooth gradients - those are NOT what we want to
#     measure for AI artefacts.
#   * We also exclude the outermost 5% of pixels because FFT edges
#     can be noisy on rectangular images and because JPEG compression
#     attenuates those bins disproportionately.
INNER_RADIUS_FRACTION = 0.25
OUTER_RADIUS_FRACTION = 0.95


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _load_grayscale(image_path: str) -> np.ndarray:
    """
    Load ``image_path`` and return it as a single-channel uint8 array.

    We force grayscale because:
      * the spectrum analysis is defined per-image, not per-channel;
      * converting to grayscale halves the work and removes the
        "which channel do we average?" ambiguity.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path!r}")
    return img


def _compute_log_spectrum(gray: np.ndarray) -> np.ndarray:
    """
    2D FFT -> shift -> log-magnitude, normalised to 0..255 uint8.

    Steps:
        1. fft2 computes the 2D FFT. The result is complex.
        2. fftshift moves the zero-frequency (DC) bin to the centre
           of the array, so low frequencies cluster in the middle
           and high frequencies fan out radially.
        3. We take the magnitude (np.abs) and discard the phase -
           we only care about energy distribution for this heuristic.
        4. log1p compresses the dynamic range. Raw FFT magnitudes
           span many orders of magnitude, so a linear scale would
           show nothing but the DC spike.
        5. We normalise to 0..255 uint8 so matplotlib can render it
           directly with a grayscale colormap.

    Returns:
        ``log_magnitude_uint8`` of shape ``(H, W)``, dtype uint8.
    """
    # float32 avoids the integer overflow np.fft has on uint8 arrays
    f = np.fft.fft2(gray.astype(np.float32))
    f_shift = np.fft.fftshift(f)
    magnitude = np.abs(f_shift)
    # log1p = log(1 + x), which handles the DC bin (magnitude can be
    # 0 in theory; log(0) would be -inf) without us having to add an
    # explicit epsilon.
    log_magnitude = np.log1p(magnitude)
    # Normalise to 0..255 uint8. ``log_magnitude.max()`` is always
    # positive (>= 0 thanks to log1p), so this is safe.
    log_magnitude -= log_magnitude.min()
    max_val = log_magnitude.max()
    if max_val > 0:
        log_magnitude = log_magnitude / max_val
    log_magnitude_uint8 = (log_magnitude * 255.0).astype(np.uint8)
    return log_magnitude_uint8


def _high_frequency_energy_ratio(gray: np.ndarray) -> float:
    """
    Return ``high_freq_energy / total_energy`` for the magnitude
    spectrum of ``gray``.

    Concretely:
        * Compute the magnitude spectrum (same as in
          ``_compute_log_spectrum`` but BEFORE the log compression -
          the log is a visualisation aid, not something we want to
          sum).
        * Build a 2D mask whose pixels are 1 inside the annulus
          ``[INNER_RADIUS_FRACTION, OUTER_RADIUS_FRACTION]`` of the
          half-spectrum radius, and 0 elsewhere.
        * high_freq_energy = sum(magnitude * mask)
        * total_energy    = sum(magnitude)
        * ratio           = high / total

    Returns:
        Float in [0, 1]. Typical natural images land somewhere in
        0.05 - 0.40. Many diffusion outputs sit higher (0.40+)
        because of the upsampling grids, but content-heavy real
        photos can land in the same range, so this is a SUPPORTING
        signal only.
    """
    magnitude = np.abs(np.fft.fftshift(np.fft.fft2(gray.astype(np.float32))))

    h, w = magnitude.shape
    # Centre of the spectrum (after fftshift, DC is at h//2, w//2).
    cy, cx = h // 2, w // 2
    # Radius of the half-spectrum (we can go either axis; use min so
    # we always fit inside the image).
    max_radius = min(cy, cx)

    # Build the radial mask once. We use a meshgrid of distances from
    # the centre and threshold it to a [0, 1] binary mask.
    yy, xx = np.ogrid[:h, :w]
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)

    inner_r = INNER_RADIUS_FRACTION * max_radius
    outer_r = OUTER_RADIUS_FRACTION * max_radius
    mask = ((dist >= inner_r) & (dist <= outer_r)).astype(np.float32)

    high_freq_energy = float(np.sum(magnitude * mask))
    total_energy = float(np.sum(magnitude))

    # Guard against the degenerate case of an all-zero image (total
    # energy = 0). Returning 0.0 is the safest fallback; the caller
    # will treat 0 as "looks smooth / natural" which is the right
    # default for a blank image.
    if total_energy <= 0.0:
        return 0.0
    return high_freq_energy / total_energy


def _save_spectrum_png(spectrum_uint8: np.ndarray, output_path: str) -> bool:
    """
    Render ``spectrum_uint8`` as a grayscale PNG at ``output_path``
    using matplotlib. Matplotlib is used (rather than cv2.imwrite)
    because it gives us a clean grayscale colormap + axis handling
    and the saved file looks like the textbook FFT visualisation
    users (and viva examiners) expect to see.

    Returns:
        True on success, False if matplotlib is unavailable or the
        save itself failed (e.g. locked file, non-writable path).
        Never raises - the entry point uses the return value to
        decide whether to expose a URL or None in the response.
    """
    try:
        import matplotlib
    except ImportError:
        logger.warning("matplotlib not installed; spectrum PNG will be skipped.")
        return False

    try:
        matplotlib.use("Agg")  # non-interactive backend, safe for servers
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - very unusual
        logger.warning("matplotlib backend init failed (%s); spectrum PNG skipped.", exc)
        return False

    try:
        fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
        ax.imshow(spectrum_uint8, cmap="gray")
        ax.set_title("FFT Magnitude Spectrum (log-scaled)")
        ax.set_xticks([])
        ax.set_yticks([])
        fig.tight_layout()
        fig.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
        return True
    except Exception as exc:
        # matplotlib sometimes errors on locked files / permission /
        # non-writable paths. Treat as "couldn't save" and let the
        # entry point return spectrum_image_path=None.
        logger.warning("matplotlib savefig failed for %s (%s)", output_path, exc)
        try:
            plt.close("all")
        except Exception:
            pass
        return False


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def _failure_dict(reason: str) -> Dict[str, Any]:
    """
    Return a NEUTRAL three-key dict for callers to use when any part
    of the frequency pipeline failed. The ratio is set to the
    FALLBACK_RATIO_ON_ERROR constant (0.20) so the combined verdict
    in main.py is not pushed toward either pole by a missing signal.
    """
    return {
        "spectrum_image_path": None,
        "high_freq_energy_ratio": FALLBACK_RATIO_ON_ERROR,
        "note": (
            f"Frequency analysis unavailable ({reason}). "
            "This is a heuristic supporting signal, not a standalone "
            "classifier, and the rest of the response (CNN + EXIF) is "
            "unaffected."
        ),
    }


def analyze_frequency(image_path: str, output_path: str) -> Dict[str, Any]:
    """
    Run the full frequency-domain pipeline on ``image_path``.

    Args:
        image_path: filesystem path to the input image.
        output_path: filesystem path where the spectrum visualization
            PNG will be written. The directory is created if missing.

    Returns:
        dict with keys::
            {
                "spectrum_image_path":     str | None,
                "high_freq_energy_ratio":  float,
                "note":                    str,
            }

        ``spectrum_image_path`` is the supplied ``output_path`` on
        success, or ``None`` if the visualization could not be
        rendered (e.g. matplotlib missing, locked file).

        ``high_freq_energy_ratio`` is the high-to-total energy ratio
        in [0, 1] on success, or ``FALLBACK_RATIO_ON_ERROR`` (0.20)
        on any failure - a neutral value that does not push the
        combined verdict either way.

        ``note`` always carries the standard "heuristic supporting
        signal" caveat, optionally prefixed with a per-failure
        explanation.

    Important:
        This is a CLASSICAL signal-processing heuristic, not a trained
        model. See the long docstring at the top of this file for
        the limitations and how to talk about them in the viva.

        This function NEVER raises (other than programming errors
        inside the helpers, which are still wrapped). The endpoint
        is therefore safe to call even on weird / broken images -
        the worst case is a neutral fallback dict and no spectrum
        PNG. The CNN and EXIF signals continue to drive the verdict.
    """
    # ---- 1. Load image ----
    try:
        gray = _load_grayscale(image_path)
    except FileNotFoundError:
        logger.warning("frequency_analysis: image not found: %s", image_path)
        return _failure_dict("image could not be read")
    except Exception as exc:
        logger.warning("frequency_analysis: image load failed (%s): %s", image_path, exc)
        return _failure_dict(f"image load failed: {exc}")

    # ---- 2. Compute the high-freq energy ratio (the cheap, always-needed stat) ----
    try:
        ratio = _high_frequency_energy_ratio(gray)
    except Exception as exc:
        logger.warning("frequency_analysis: FFT energy ratio failed: %s", exc)
        return _failure_dict(f"FFT energy ratio failed: {exc}")

    # ---- 3. Compute the log-magnitude spectrum for the PNG ----
    try:
        spectrum_uint8 = _compute_log_spectrum(gray)
    except Exception as exc:
        # We have the ratio but can't render the PNG - still useful
        # for the verdict, just no visualization.
        logger.warning("frequency_analysis: log spectrum computation failed: %s", exc)
        return {
            "spectrum_image_path": None,
            "high_freq_energy_ratio": float(ratio),
            "note": STANDARD_HEURISTIC_NOTE,
        }

    # ---- 4. Save the PNG (may fail gracefully if matplotlib is missing) ----
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as exc:
            logger.warning("frequency_analysis: could not create %s (%s)", out_dir, exc)
            return {
                "spectrum_image_path": None,
                "high_freq_energy_ratio": float(ratio),
                "note": STANDARD_HEURISTIC_NOTE,
            }

    saved_ok = _save_spectrum_png(spectrum_uint8, output_path)
    return {
        "spectrum_image_path": output_path if saved_ok else None,
        "high_freq_energy_ratio": float(ratio),
        "note": STANDARD_HEURISTIC_NOTE,
    }
