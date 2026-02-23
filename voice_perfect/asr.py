"""Local faster-whisper wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List


def transcribe(audio_path: Path, model_size: str = "small", language: str = "zh") -> List[Dict]:
    """Transcribe audio with faster-whisper and return segment dicts (with words when available)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - dependency issue in runtime
        raise RuntimeError(
            "faster-whisper is not installed. Please install dependencies first."
        ) from exc

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=False,
        beam_size=5,
    )

    out: List[Dict] = []
    for idx, segment in enumerate(segments):
        words = []
        for word in getattr(segment, "words", []) or []:
            words.append(
                {
                    "word": (word.word or "").strip(),
                    "start": float(word.start) if word.start is not None else None,
                    "end": float(word.end) if word.end is not None else None,
                }
            )

        out.append(
            {
                "index": idx,
                "start": float(segment.start),
                "end": float(segment.end),
                "text": (segment.text or "").strip(),
                "words": words,
            }
        )
    return out
