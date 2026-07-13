"""Lightweight language detection for chunk text.

Uses CJK character ratio heuristic — no external dependencies.
Suitable for Chinese/English mixed-content documents.

Detection logic:
  - Count CJK ideographs, Latin letters, and other characters.
  - If CJK ratio > 30% and Latin ratio > 30% → "zh-en" (mixed).
  - If CJK ratio > 30% → "zh".
  - Otherwise → "en".

This is intentionally simple. For production-grade detection consider
``langdetect`` or ``fasttext-langdetect``, but those add dependencies
and are unnecessary for a zh/en bilingual system.
"""

from __future__ import annotations

import re
import unicodedata

# CJK Unified Ideographs (U+4E00–U+9FFF) + extensions A + B +
# CJK Compatibility Ideographs + Hiragana/Katakana (for robustness).
_CJK_PATTERN = re.compile(
    r"[\u3040-\u30ff"      # Hiragana + Katakana
    r"\u3400-\u4dbf"       # CJK Ext A
    r"\u4e00-\u9fff"       # CJK Unified Ideographs
    r"\uf900-\ufaff"       # CJK Compatibility Ideographs
    r"]"
)

_LATIN_PATTERN = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> str:
    """Detect the dominant language of *text*.

    Args:
        text: Input text (any length, UTF-8 string).

    Returns:
        One of ``"zh"``, ``"en"``, ``"zh-en"`` (mixed), or ``"unknown"``
        if the text is too short to determine.
    """
    if not text or len(text.strip()) < 2:
        return "unknown"

    cjk_count = len(_CJK_PATTERN.findall(text))
    latin_count = len(_LATIN_PATTERN.findall(text))
    total = cjk_count + latin_count

    if total == 0:
        return "unknown"

    cjk_ratio = cjk_count / total
    latin_ratio = latin_count / total

    if cjk_ratio > 0.3 and latin_ratio > 0.3:
        return "zh-en"
    if cjk_ratio > 0.3:
        return "zh"
    return "en"


def detect_language_batch(texts: list[str]) -> list[str]:
    """Detect language for a batch of texts.

    Args:
        texts: List of text strings.

    Returns:
        List of language codes, same length as input.
    """
    return [detect_language(t) for t in texts]
