"""Local faster-whisper wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List


def transcribe(audio_path: Path, model_size: str = "small", language: str = "zh") -> List[Dict]:
    """Transcribe audio with faster-whisper and return segment dicts."""
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
        vad_filter=False,
        word_timestamps=True,
    )

    out: List[Dict] = []
    for idx, segment in enumerate(segments):
        out.append(
            {
                "index": idx,
                "start": float(segment.start),
                "end": float(segment.end),
                "text": (segment.text or "").strip(),
            }
        )
    return out
