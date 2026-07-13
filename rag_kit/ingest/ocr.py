"""OCR fallback for scanned PDFs and image-based documents.

Uses EasyOCR with Chinese (simplified) + English language support.
The EasyOCR reader is lazy-loaded and cached for the process lifetime
to avoid repeated model-loading overhead.

If EasyOCR is not installed, falls back to pytesseract. If neither is
available, raises ImportError with a clear message.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)

# Module-level cache for the OCR reader — avoids re-loading on every page.
_ocr_reader: Any = None
_ocr_engine: str = ""  # "easyocr" or "pytesseract"


def _get_easyocr_reader(languages: list[str]):
    """Lazy-load and cache an EasyOCR reader.

    EasyOCR uses language codes like 'ch_sim', 'en'. We map our config
    codes ('zh', 'en') to EasyOCR's expected format.
    """
    global _ocr_reader, _ocr_engine

    if _ocr_reader is not None and _ocr_engine == "easyocr":
        return _ocr_reader

    # Map config language codes to EasyOCR codes.
    easyocr_langs: list[str] = []
    for lang in languages:
        if lang == "zh":
            easyocr_langs.append("ch_sim")
        elif lang == "en":
            easyocr_langs.append("en")
        else:
            easyocr_langs.append(lang)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for l in easyocr_langs:
        if l not in seen:
            seen.add(l)
            deduped.append(l)

    logger.info("Loading EasyOCR reader for languages: %s", deduped)
    import easyocr

    _ocr_reader = easyocr.Reader(deduped, gpu=False, verbose=False)
    _ocr_engine = "easyocr"
    return _ocr_reader


def _ocr_with_easyocr(
    image: Image.Image,
    languages: list[str],
) -> str:
    """Run EasyOCR on a PIL Image and return extracted text."""
    reader = _get_easyocr_reader(languages)
    import numpy as np
    results = reader.readtext(np.asarray(image))
    # EasyOCR returns list of (bbox, text, confidence) tuples.
    texts = [item[1] for item in results if len(item) >= 2]
    return "\n".join(texts)


def _ocr_with_pytesseract(
    image: Image.Image,
    languages: list[str],
) -> str:
    """Run pytesseract on a PIL Image and return extracted text."""
    import pytesseract

    # Map config codes to tesseract language codes.
    tess_langs: list[str] = []
    for lang in languages:
        if lang == "zh":
            tess_langs.append("chi_sim")
        elif lang == "en":
            tess_langs.append("eng")
        else:
            tess_langs.append(lang)
    lang_str = "+".join(tess_langs) if tess_langs else "eng"

    return pytesseract.image_to_string(image, lang=lang_str)


def ocr_image(
    image: Image.Image,
    languages: list[str] | None = None,
) -> str:
    """Run OCR on a PIL Image, returning extracted text.

    Tries EasyOCR first (preferred for Chinese+English), falls back to
    pytesseract if EasyOCR is not available.

    Args:
        image:     PIL Image to OCR.
        languages: List of language codes from config (e.g. ``["zh", "en"]``).

    Returns:
        Extracted text string (may be empty if no text found).

    Raises:
        ImportError: If neither EasyOCR nor pytesseract is installed.
    """
    if languages is None:
        languages = ["zh", "en"]

    # Try EasyOCR first.
    try:
        import easyocr  # noqa: F401

        return _ocr_with_easyocr(image, languages)
    except ImportError:
        pass

    # Fall back to pytesseract.
    try:
        import pytesseract  # noqa: F401

        return _ocr_with_pytesseract(image, languages)
    except ImportError:
        pass

    raise ImportError(
        "No OCR engine available. Install one of:\n"
        "  pip install easyocr    (recommended, supports Chinese+English)\n"
        "  pip install pytesseract  (requires tesseract-ocr system package)"
    )


def is_ocr_available() -> bool:
    """Check if any OCR engine is available."""
    try:
        import easyocr  # noqa: F401

        return True
    except ImportError:
        pass
    try:
        import pytesseract  # noqa: F401

        return True
    except ImportError:
        pass
    return False

