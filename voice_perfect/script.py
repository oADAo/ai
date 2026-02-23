"""Script normalization and sentence splitting utilities."""

from __future__ import annotations

import re
import unicodedata
from typing import List

SENTENCE_SEP_RE = re.compile(r"([。！？!?；;\n]+)")


def normalize_text(text: str) -> str:
    """Normalize script/ASR text for robust matching.

    - NFKC full/half width normalization
    - Unify quote variants and punctuation spacing
    - Collapse repeated whitespace
    """
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "，": ",",
        "。": ".",
        "：": ":",
        "；": ";",
        "！": "!",
        "？": "?",
        "「": '"',
        "」": '"',
        "『": '"',
        "』": '"',
        "（": "(",
        "）": ")",
        "、": ",",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text: str, max_len: int = 40) -> List[str]:
    """Split a script into short sentence chunks for alignment.

    Splits by Chinese/English punctuation first, then length-based fallback.
    """
    normalized = normalize_text(text)
    if not normalized:
        return []

    tokens = SENTENCE_SEP_RE.split(normalized)
    chunks: List[str] = []
    current = ""

    for token in tokens:
        if not token:
            continue
        current += token
        if SENTENCE_SEP_RE.fullmatch(token):
            chunk = current.strip(" ,")
            if chunk:
                chunks.extend(_split_by_length(chunk, max_len))
            current = ""

    if current.strip():
        chunks.extend(_split_by_length(current.strip(" ,"), max_len))

    return [c for c in (c.strip() for c in chunks) if c]


def _split_by_length(text: str, max_len: int) -> List[str]:
    if len(text) <= max_len:
        return [text]

    parts: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_len, len(text))
        window = text[start:end]
        cut = max(window.rfind(","), window.rfind("."), window.rfind(";"), window.rfind(" "))
        if cut > max_len // 2:
            end = start + cut + 1
        parts.append(text[start:end].strip())
        start = end
    return [p for p in parts if p]
