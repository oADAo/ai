"""Build keep intervals and final plan JSON payload."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


def build_keep_intervals(
    asr_segments: Sequence[Dict],
    alignment: Sequence[Dict],
    silence_intervals: Sequence[Tuple[float, float]],
    pad: float,
    merge_gap: float,
    max_seg_sec: float,
) -> List[Tuple[float, float]]:
    matched_ranges: List[Tuple[float, float]] = []
    for item in alignment:
        if item["operation"] != "MATCH":
            continue
        seg = asr_segments[item["asr_index"]]
        start = max(0.0, seg["start"] - pad)
        end = max(start, seg["end"] + pad)
        matched_ranges.append((start, end))

    merged = _merge_intervals(sorted(matched_ranges), merge_gap)
    split = []
    for start, end in merged:
        if end - start <= max_seg_sec:
            split.append((start, end))
            continue
        split.extend(_split_long_interval(start, end, silence_intervals, max_seg_sec))
    return split


def _merge_intervals(intervals: Iterable[Tuple[float, float]], merge_gap: float) -> List[Tuple[float, float]]:
    intervals = list(intervals)
    if not intervals:
        return []
    out = [intervals[0]]
    for start, end in intervals[1:]:
        prev_start, prev_end = out[-1]
        if start - prev_end <= merge_gap:
            out[-1] = (prev_start, max(prev_end, end))
        else:
            out.append((start, end))
    return out


def _split_long_interval(
    start: float,
    end: float,
    silence_intervals: Sequence[Tuple[float, float]],
    max_seg_sec: float,
) -> List[Tuple[float, float]]:
    pieces = []
    cursor = start
    while cursor < end:
        target = min(cursor + max_seg_sec, end)
        candidates = [
            s for s, _ in silence_intervals if cursor + 1.0 < s < target - 0.2
        ]
        if candidates:
            cut = candidates[-1]
        else:
            cut = target
        if cut <= cursor:
            cut = target
        pieces.append((cursor, cut))
        cursor = cut
    return pieces


def build_silence_only_keep_intervals(
    silence_intervals: Sequence[Tuple[float, float]],
    audio_duration: float,
    silence_dur_threshold: float,
) -> List[Tuple[float, float]]:
    """Fallback mode: remove long silences only."""
    if audio_duration <= 0:
        return []

    long_silences = [
        (start, end) for start, end in silence_intervals if (end - start) >= silence_dur_threshold
    ]
    if not long_silences:
        return [(0.0, audio_duration)]

    keep = []
    cursor = 0.0
    for start, end in long_silences:
        if start > cursor:
            keep.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < audio_duration:
        keep.append((cursor, audio_duration))
    return keep


def make_plan_payload(
    *,
    input_audio: Path,
    asr_audio: Path,
    script_sentences: Sequence[str],
    asr_segments: Sequence[Dict],
    alignment: Sequence[Dict],
    keep_intervals: Sequence[Tuple[float, float]],
    notes: Dict,
) -> Dict:
    return {
        "input_audio": str(input_audio),
        "asr_audio": str(asr_audio),
        "script_sentences": [
            {"index": i, "text": sentence} for i, sentence in enumerate(script_sentences)
        ],
        "asr_segments": list(asr_segments),
        "alignment": list(alignment),
        "keep_intervals": [
            {"start": round(start, 3), "end": round(end, 3)}
            for start, end in keep_intervals
        ],
        "notes": notes,
    }
