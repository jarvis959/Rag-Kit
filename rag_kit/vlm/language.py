"""Language detection for VLM captioning.

Determines whether surrounding document content is Chinese (zh) or English (en)
so that VLM-generated descriptions match the document's language.
"""

from __future__ import annotations

import re
import unicodedata

# CJK Unicode block ranges
_CJK_RANGES = [
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0x3400, 0x4DBF),    # CJK Extension A
    (0x20000, 0x2A6DF),  # CJK Extension B
    (0x2A700, 0x2B73F),  # CJK Extension C
    (0x2B740, 0x2B81F),  # CJK Extension D
    (0x3000, 0x303F),    # CJK Symbols and Punctuation
    (0xFF00, 0xFFEF),    # Full-width Forms
]


def _is_cjk_char(code: int) -> bool:
    """Check if a Unicode code point is a CJK character."""
    for start, end in _CJK_RANGES:
        if start <= code <= end:
            return True
    return False


def detect_language(text: str) -> str:
    """Detect the dominant language of a text snippet.

    Uses CJK character ratio as the primary signal:
    - If >20% of non-whitespace characters are CJK, return "zh"
    - Otherwise return "en"

    This is intentionally simple — we only need zh vs en to pick
    the VLM prompt language. For mixed-language documents, the
    dominant language wins.

    Args:
        text: A sample of surrounding document text.

    Returns:
        "zh" or "en".
    """
    if not text:
        return "en"

    # Normalize to strip accents/diacritics
    text = unicodedata.normalize("NFKC", text)

    cjk_count = 0
    total_count = 0
    for char in text:
        if char.isspace() or char in ".,;:!?\"'()[]{}<>/\\@#$%^&*+=|~`":
            continue
        total_count += 1
        if _is_cjk_char(ord(char)):
            cjk_count += 1

    if total_count == 0:
        return "en"

    cjk_ratio = cjk_count / total_count
    return "zh" if cjk_ratio > 0.20 else "en"


def get_vlm_prompt(language: str) -> str:
    """Return the VLM captioning prompt in the appropriate language.

    Args:
        language: "zh" or "en"

    Returns:
        Prompt string for the VLM model.
    """
    if language == "zh":
        return (
            "这是文档中的一页。请用中文描述你在图片中看到的内容。"
            "重点关注图表、图形、示意图、表格和任何视觉内容。"
            "如果可见，请包含数据标签、轴标题和趋势。描述要简洁但信息丰富。"
        )
    return (
        "This is a page from a document. Describe what you see in this image "
        "for search purposes. Focus on charts, graphs, diagrams, tables, "
        "figures, and any visual content. Include data labels, axis titles, "
        "and trends if visible. Be concise but descriptive."
    )
