"""Utilities for ffmpeg preprocessing, silence detection and command generation."""

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


def run_cmd(cmd: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def preprocess_to_mono16k(input_audio: Path, output_audio: Path) -> Path:
    cmd = ["ffmpeg", "-y", "-i", str(input_audio), "-ac", "1", "-ar", "16000", str(output_audio)]
    run_cmd(cmd)
    return output_audio


def detect_silence(audio_path: Path, silence_db: float, silence_dur: float) -> List[Tuple[float, float]]:
    cmd = [
        "ffmpeg",
        "-i",
        str(audio_path),
        "-af",
        f"silencedetect=noise={silence_db}dB:d={silence_dur}",
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    stderr = proc.stderr

    start_re = re.compile(r"silence_start: (?P<v>[0-9.]+)")
    end_re = re.compile(r"silence_end: (?P<v>[0-9.]+)")

    starts = [float(m.group("v")) for m in start_re.finditer(stderr)]
    ends = [float(m.group("v")) for m in end_re.finditer(stderr)]

    intervals = []
    for idx, start in enumerate(starts):
        if idx < len(ends):
            intervals.append((start, ends[idx]))
    return intervals


def build_filter_complex(keep_intervals: Iterable[Tuple[float, float]]) -> str:
    intervals = list(keep_intervals)
    if not intervals:
        return ""

    chains = []
    labels = []
    for idx, (start, end) in enumerate(intervals):
        lbl = f"a{idx}"
        labels.append(f"[{lbl}]")
        chains.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[{lbl}]")

    concat = f"{''.join(labels)}concat=n={len(intervals)}:v=0:a=1[out]"
    return "; ".join(chains + [concat])


def build_ffmpeg_command(input_audio: Path, output_audio: Path, keep_intervals: Iterable[Tuple[float, float]]) -> List[str]:
    filter_complex = build_filter_complex(keep_intervals)
    if not filter_complex:
        raise ValueError("No keep intervals available for ffmpeg command")

    return ["ffmpeg", "-y", "-i", str(input_audio), "-filter_complex", filter_complex, "-map", "[out]", str(output_audio)]


def to_shell_line(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def to_powershell_line(cmd: Sequence[str]) -> str:
    escaped = []
    for part in cmd:
        escaped.append('"' + part.replace('"', '`"') + '"')
    return " ".join(escaped)
