"""Ingestion sub-package — text extraction, OCR, and file processing.

Public API:
    ingest_file           — parse a single file, return chunk dicts
    ingest_folder         — parse all supported files in a folder
    extract_text          — low-level: extract raw text from a single file
    SUPPORTED_EXTENSIONS  — tuple of supported file extensions
    detect_language       — detect zh/en/zh-en from text
    ocr_image             — run OCR on a PIL image (EasyOCR/pytesseract)
    is_ocr_available      — check if any OCR engine is installed
"""

from rag_kit.ingest.pipeline import (
    SUPPORTED_EXTENSIONS,
    extract_text,
    ingest_file,
    ingest_folder,
)
from rag_kit.ingest.language import detect_language, detect_language_batch
from rag_kit.ingest.ocr import is_ocr_available, ocr_image

__all__ = [
    "SUPPORTED_EXTENSIONS",
    "ingest_file",
    "ingest_folder",
    "extract_text",
    "detect_language",
    "detect_language_batch",
    "ocr_image",
    "is_ocr_available",
]
