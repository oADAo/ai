"""Script normalization and sentence splitting utilities."""

from __future__ import annotations

import re
import unicodedata
from typing import List

# Include both CJK and ASCII punctuation after normalization.
SENTENCE_SEP_RE = re.compile(r"([。！？!?；;\.\n]+)")

FILLER_TOKENS = {
    "嗯",
    "呃",
    "額",
    "啊",
    "喔",
    "哦",
    "這個",
    "那個",
    "然後",
    "就是",
}


def normalize_text(text: str) -> str:
    """Normalize script/ASR text for robust matching."""
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


def tokenize_for_match(text: str) -> List[str]:
    normalized = normalize_text(text).lower()
    # Keep CJK as single chars + alnum words.
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", normalized)
    return [t for t in tokens if t]


def strip_fillers_for_match(text: str) -> str:
    """Remove known filler words from matching string to improve alignment robustness."""
    normalized = normalize_text(text)
    for filler in sorted(FILLER_TOKENS, key=len, reverse=True):
        normalized = normalized.replace(filler, "")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def split_sentences(text: str, max_len: int = 40) -> List[str]:
    """Split a script into short sentence chunks for alignment."""
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
