"""
EXIF Metadata Analysis Module
=============================

WHAT THIS MODULE DOES
---------------------
Inspects the image's EXIF metadata for forensic signals that often
correlate with AI-generated images:

    1. Completely missing EXIF block (most diffusion models strip it
       by default, but so do screenshots and edited real photos).
    2. A "Software" tag whose value names a known diffusion tool
       (Stable Diffusion, Midjourney, DALL-E, ComfyUI, Automatic1111,
       etc.) - basically a smoking gun when present.
    3. Camera make / model missing OR nonsensical, while other EXIF
       fields (like DateTime, lens, exposure) still look photographic
       - this is the "Frankenstein" profile some AI pipelines produce.

It returns a discrete ``risk_score`` of "Low" | "Medium" | "High"
plus a list of plain-English ``risk_reasons`` the frontend (and your
project report) can quote verbatim.

====================================================================
!! IMPORTANT - HEURISTIC ONLY, NOT A STANDALONE DETECTOR !!
====================================================================
EXIF metadata is one of the *easiest* signals to defeat or fake:

    * Re-saving an image through any image editor (Photoshop, GIMP,
      even some phone gallery apps) will silently strip large chunks
      of EXIF.
    * Most social-media platforms (Twitter, Discord, WhatsApp, etc.)
      re-encode uploads and remove EXIF entirely.
    * Conversely, attackers can *inject* a fake "Software: Adobe
      Photoshop" tag to disguise a diffusion output as a real photo.
    * Genuine AI images that go through "EXIF restoration" tools
      will look perfectly photographic metadata-wise.

For these reasons this module MUST be treated as a SUPPORTING
heuristic, never as a reliable detector on its own. The CNN
prediction (which actually learned from labelled pixels) carries the
bulk of the weight in the combined verdict; EXIF only nudges it.

For your project report you can honestly say:

    "The EXIF analysis is a lightweight, rule-based forensic signal.
     It is intentionally low-weight in the combined verdict because
     EXIF metadata is trivially stripped or forged, and its absence
     is equally common in legitimate screenshots and edited photos.
     It is included to surface *corroborating* evidence - e.g. an
     image that the CNN flagged as AI AND that also has a
     'Software: stable-diffusion-webui' tag - rather than to make
     a definitive call on its own."

====================================================================
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    # Pillow is the only hard dependency for this module.
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError as exc:  # pragma: no cover - Pillow is in requirements.txt
    raise ImportError(
        "Pillow is required for exif_analysis. Install with: pip install Pillow"
    ) from exc


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

# Canonical list of diffusion / generative-tool names we treat as a
# smoking gun when they appear (case-insensitively) in the "Software"
# EXIF tag. Add to this list as new tools become mainstream.
#
# We list BOTH the hyphenated and space-separated variants of each
# name, because the matching code below normalises hyphens to spaces
# in the input string before checking. Listing both forms here keeps
# the match readable and avoids confusion about which form is the
# "real" token.
#
# Why these specific names?
#   * "stable diffusion" / "automatic1111" / "comfyui" - the dominant
#     open-source Stable Diffusion UIs leave this tag in by default.
#   * "midjourney" - Midjourney exports PNGs that include a
#     "Software: Midjourney ..." tag (often with a job id).
#   * "dall-e" / "dalle" - both spellings appear; the hyphenated
#     version is the official product name, the un-hyphenated one
#     is the casual / community spelling.
SUSPICIOUS_SOFTWARE_TOKENS = (
    "stable diffusion",  # also matches "stable-diffusion-webui" after hyphen->space
    "midjourney",
    "dall e",            # matches "DALL-E", "dall-e", "Dall E"
    "dalle",             # matches the un-hyphenated spelling "DALL-E generator"
    "comfyui",
    "automatic1111",
)


# Tags whose presence + camera absence looks "Frankenstein":
# a real camera writes these almost always. If they show up *without*
# a make/model we treat the metadata as inconsistent.
PHOTOGRAPHIC_LOOKING_TAGS = (
    "ExposureTime",
    "FNumber",
    "ISOSpeedRatings",
    "FocalLength",
    "DateTime",
    "DateTimeOriginal",
    "LensMake",
    "LensModel",
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _tag_name(tag_id: int) -> str:
    """Translate a numeric EXIF tag id to its human-readable name."""
    return TAGS.get(tag_id, str(tag_id))


def _decode_if_bytes(value: Any) -> Any:
    """
    EXIF string values often come back as ``bytes`` (especially from
    JPEG, less so from PNG/WEBP). Decode them defensively; non-string
    values are returned unchanged.
    """
    if isinstance(value, bytes):
        for encoding in ("utf-8", "latin-1", "ascii"):
            try:
                return value.decode(encoding).strip("\x00").strip()
            except UnicodeDecodeError:
                continue
        # Last resort - hex repr so the UI doesn't blow up.
        return value.hex()
    if isinstance(value, str):
        return value.strip("\x00").strip()
    return value


def _extract_exif(image_path: str) -> Optional[Dict[str, Any]]:
    """
    Open ``image_path`` with Pillow and return its EXIF block as a
    ``{tag_name: decoded_value}`` dict.

    Returns:
        ``None`` if the file can't be opened, or if it has no EXIF
        block at all. Callers should treat ``None`` as a meaningful
        signal in itself (see the ambiguity note in the module
        docstring: missing EXIF is common in BOTH AI images AND
        screenshots / social-media uploads of real photos).
    """
    try:
        with Image.open(image_path) as img:
            exif_raw = img.getexif()
    except (OSError, ValueError):
        # OSError: corrupt / unreadable file
        # ValueError: Pillow raises this for some malformed headers
        return None

    if not exif_raw:
        return None  # No EXIF block at all - not even an empty one.

    decoded: Dict[str, Any] = {}
    for tag_id, value in exif_raw.items():
        decoded[_tag_name(tag_id)] = _decode_if_bytes(value)
    return decoded


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def analyze_exif(image_path: str) -> Dict[str, Any]:
    """
    Analyse the EXIF metadata of ``image_path`` for AI-image red flags.

    Args:
        image_path: filesystem path to the uploaded image.

    Returns:
        A dict with the keys::

            {
                "has_exif":        bool,                # was an EXIF block present at all?
                "camera_make":     str | None,          # tag 0x010F
                "camera_model":    str | None,          # tag 0x0110
                "software":        str | None,          # tag 0x0131 (decoded)
                "risk_score":      "Low" | "Medium" | "High",
                "risk_reasons":    list[str],           # human-readable signals
            }

    Important:
        The ``risk_score`` here is a HEURISTIC supporting signal -
        see the long docstring at the top of this file for the
        honest discussion of why EXIF must never be used as a
        standalone detector. It is intentionally low-weight in
        the combined verdict in main.py.

    The function never raises on bad files: it returns the
    "no EXIF + Medium risk" shape for anything it can't read,
    so the calling endpoint can still serve a response.
    """
    reasons: List[str] = []
    risk_score = "Low"  # default; we escalate only if we find evidence.

    exif = _extract_exif(image_path)

    # ---- Missing EXIF block ----
    # NOTE on ambiguity: a missing EXIF block is a *very* common
    # attribute of AI-generated images (most diffusion pipelines
    # don't write any), BUT it is equally common for:
    #   - screenshots
    #   - images downloaded from social media (Twitter/Discord/etc.
    #     strip metadata server-side)
    #   - photos that have been edited in any tool that re-saves
    #     the file (Photoshop, GIMP, Lightroom export, phone
    #     gallery apps, ...)
    # So we score this as Medium on its own - enough to flag for
    # the user, not enough to convict.
    if exif is None or len(exif) == 0:
        reasons.append(
            "No EXIF metadata was found. This is common for AI-generated "
            "images, but also for screenshots, social-media re-uploads, "
            "and photos that have been edited and re-saved."
        )
        # Without any other evidence we can only call it Medium.
        return {
            "has_exif": False,
            "camera_make": None,
            "camera_model": None,
            "software": None,
            "risk_score": "Medium",
            "risk_reasons": reasons,
        }

    # We have SOME EXIF. Pull the fields we care about.
    camera_make = exif.get("Make") or None
    camera_model = exif.get("Model") or None
    software = exif.get("Software") or None

    # Normalise to strings for the response.
    if camera_make is not None and not isinstance(camera_make, str):
        camera_make = str(camera_make)
    if camera_model is not None and not isinstance(camera_model, str):
        camera_model = str(camera_model)
    if software is not None and not isinstance(software, str):
        software = str(software)

    # ---- Red flag 2: suspicious "Software" tag ----
    # If the image *claims* it was made by a known diffusion tool,
    # that's a smoking gun. We escalate to High immediately.
    if software:
        # Normalise hyphens to spaces so "stable-diffusion-webui",
        # "Stable Diffusion WebUI", and "stable diffusion" all match
        # the same token. Otherwise the substring check below misses
        # hyphenated variants of the tool name.
        software_lower = software.lower().replace("-", " ")
        for token in SUSPICIOUS_SOFTWARE_TOKENS:
            if token in software_lower:
                reasons.append(
                    f"Software tag names a known generative-AI tool: "
                    f"{software!r} (matched keyword {token!r})."
                )
                risk_score = "High"
                break

    # ---- Red flag 3: inconsistent / missing camera metadata ----
    # A real camera almost always writes Make + Model together with
    # photographic-looking fields (ExposureTime, FNumber, ISO, lens
    # info, DateTime). If we have *those* photographic fields but the
    # camera is unidentified, the profile is suspicious - it could
    # be a diffusion pipeline that copied some metadata from a
    # reference photo without copying the camera identity.
    has_make = bool(camera_make and camera_make.strip())
    has_model = bool(camera_model and camera_model.strip())
    photo_tag_count = sum(
        1 for tag in PHOTOGRAPHIC_LOOKING_TAGS if exif.get(tag) is not None
    )

    if not has_make and not has_model and photo_tag_count >= 2:
        reasons.append(
            f"Camera make/model are missing, but {photo_tag_count} other "
            f"photographic-looking EXIF fields are present (e.g. exposure, "
            f"ISO, lens, datetime). This inconsistent profile is unusual "
            f"for a real camera photo."
        )
        # Escalate to Medium at minimum; to High if we already had a
        # smoking-gun software tag, otherwise leave at Medium.
        if risk_score == "Low":
            risk_score = "Medium"

    # Also note if the make/model are *present but suspicious* -
    # e.g. some diffusion tools write literal strings like
    # "Stable Diffusion" into the Make or Model field. We only
    # flag this if we haven't already flagged it via the Software
    # tag above, to avoid double-counting.
    for field_name, field_value in (("Make", camera_make), ("Model", camera_model)):
        if not field_value:
            continue
        # Same hyphen-normalisation trick as for the Software tag.
        lower = field_value.lower().replace("-", " ")
        # Has the Software tag already raised a High? Then this would
        # be redundant noise - skip.
        already_high = risk_score == "High"
        if already_high:
            continue
        for token in SUSPICIOUS_SOFTWARE_TOKENS:
            if token in lower:
                reasons.append(
                    f"Camera {field_name} field contains a generative-AI "
                    f"keyword: {field_value!r} (matched {token!r})."
                )
                if risk_score == "Low":
                    risk_score = "Medium"
                break

    # If we found nothing suspicious at all, keep risk_score = "Low"
    # and make sure reasons is a non-empty list so the UI can show
    # something reassuring ("No red flags detected").
    if not reasons:
        reasons.append(
            "No EXIF red flags detected. Note that this does NOT confirm "
            "the image is real - EXIF can be stripped, faked, or absent "
            "for many legitimate reasons."
        )

    return {
        "has_exif": True,
        "camera_make": camera_make,
        "camera_model": camera_model,
        "software": software,
        "risk_score": risk_score,
        "risk_reasons": reasons,
    }
