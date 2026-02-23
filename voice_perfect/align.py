"""Monotonic alignment between ASR segments and script sentences."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Sequence

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - fallback for offline environments
    fuzz = None

from .script import normalize_text


@dataclass
class AlignmentItem:
    asr_index: int
    operation: str  # MATCH or DELETE
    script_index: Optional[int]
    score: float


def _simple_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio() * 100.0


def similarity(a: str, b: str) -> float:
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    if fuzz is None:
        return _simple_ratio(a_norm, b_norm)
    ratio = fuzz.ratio(a_norm, b_norm)
    token = fuzz.token_set_ratio(a_norm, b_norm)
    return (ratio * 0.6) + (token * 0.4)


def align_segments_to_script(
    asr_segments: Sequence[Dict],
    script_sentences: Sequence[str],
    match_threshold: float = 55.0,
) -> Dict:
    """Align ASR segments to script sentences via DP."""
    n = len(asr_segments)
    m = len(script_sentences)

    dp = [[float("-inf")] * (m + 1) for _ in range(n + 1)]
    back: List[List[Optional[tuple]]] = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0

    insert_penalty = 15.0
    delete_penalty = 10.0

    for i in range(n + 1):
        for j in range(m + 1):
            base = dp[i][j]
            if base == float("-inf"):
                continue

            if i < n:
                cand = base - delete_penalty
                if cand > dp[i + 1][j]:
                    dp[i + 1][j] = cand
                    back[i + 1][j] = (i, j, "DELETE", None, 0.0)

            if j < m:
                cand = base - insert_penalty
                if cand > dp[i][j + 1]:
                    dp[i][j + 1] = cand
                    back[i][j + 1] = (i, j, "INSERT", j, 0.0)

            if i < n and j < m:
                score = similarity(asr_segments[i]["text"], script_sentences[j])
                bonus = (i / max(1, n - 1 if n > 1 else 1)) * 12.0
                cand = base + score + bonus
                if cand > dp[i + 1][j + 1]:
                    dp[i + 1][j + 1] = cand
                    back[i + 1][j + 1] = (i, j, "MATCH", j, score)

    end_j = max(range(m + 1), key=lambda col: dp[n][col])
    i, j = n, end_j
    ops = []
    while i > 0 or j > 0:
        prev = back[i][j]
        if prev is None:
            break
        pi, pj, op, script_idx, score = prev
        ops.append((pi, op, script_idx, score))
        i, j = pi, pj

    ops.reverse()

    alignment: List[AlignmentItem] = []
    matched_script = set()
    for asr_idx, op, script_idx, score in ops:
        if op == "MATCH" and script_idx is not None and score >= match_threshold:
            alignment.append(AlignmentItem(asr_idx, "MATCH", script_idx, round(score, 2)))
            matched_script.add(script_idx)
        elif op in {"MATCH", "DELETE"}:
            alignment.append(AlignmentItem(asr_idx, "DELETE", None, round(score, 2)))

    inserted_script = [idx for idx in range(m) if idx not in matched_script]

    return {
        "alignment": [item.__dict__ for item in alignment],
        "missing_script_indices": inserted_script,
    }
