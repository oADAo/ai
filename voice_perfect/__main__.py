"""CLI entrypoint for voice_perfect."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .align import align_segments_to_script
from .asr import transcribe
from .ffmpeg_utils import (
    build_ffmpeg_command,
    detect_silence,
    preprocess_to_mono16k,
    to_powershell_line,
    to_shell_line,
)
from .plan import (
    build_keep_intervals,
    build_silence_only_keep_intervals,
    make_plan_payload,
)
from .script import split_sentences


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Script-aligned WAV cleanup tool")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--run-ffmpeg", action="store_true")
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--silence-db", type=float, default=-35.0)
    parser.add_argument("--silence-dur", type=float, default=0.35)
    parser.add_argument("--pad", type=float, default=0.08)
    parser.add_argument("--merge-gap", type=float, default=0.20)
    parser.add_argument("--max-seg-sec", type=float, default=12.0)
    return parser.parse_args()


def _probe_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    proc = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return float(proc.stdout.strip())


def main() -> None:
    args = parse_args()
    input_audio = Path(args.audio).resolve()
    script_path = Path(args.script).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    asr_audio = out_dir / "asr_input_16k_mono.wav"
    preprocess_to_mono16k(input_audio, asr_audio)

    silence_intervals = detect_silence(asr_audio, args.silence_db, args.silence_dur)
    script_text = script_path.read_text(encoding="utf-8")
    script_sentences = split_sentences(script_text)

    notes = {}
    fallback_used = False

    try:
        asr_segments = transcribe(asr_audio, model_size=args.model, language=args.language)
        aligned = align_segments_to_script(asr_segments, script_sentences)
        keep_intervals = build_keep_intervals(
            asr_segments,
            aligned["alignment"],
            silence_intervals,
            pad=args.pad,
            merge_gap=args.merge_gap,
            max_seg_sec=args.max_seg_sec,
        )
        notes["missing_script_indices"] = aligned["missing_script_indices"]
        alignment_rows = aligned["alignment"]
    except Exception as exc:  # fallback required by spec
        fallback_used = True
        asr_segments = []
        alignment_rows = []
        duration = _probe_duration(asr_audio)
        keep_intervals = build_silence_only_keep_intervals(
            silence_intervals,
            audio_duration=duration,
            silence_dur_threshold=args.silence_dur,
        )
        notes["fallback"] = "alignment_failed_silence_only"
        notes["error"] = str(exc)

    if not keep_intervals:
        raise RuntimeError("No keep intervals generated; please check audio/script quality.")

    plan = make_plan_payload(
        input_audio=input_audio,
        asr_audio=asr_audio,
        script_sentences=script_sentences,
        asr_segments=asr_segments,
        alignment=alignment_rows,
        keep_intervals=keep_intervals,
        notes=notes,
    )
    (out_dir / "plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    final_wav = out_dir / "final.wav"
    ffmpeg_cmd = build_ffmpeg_command(input_audio, final_wav, keep_intervals)
    (out_dir / "ffmpeg_cmd_mac.sh").write_text(to_shell_line(ffmpeg_cmd) + "\n", encoding="utf-8")
    (out_dir / "ffmpeg_cmd_win.ps1").write_text(to_powershell_line(ffmpeg_cmd) + "\n", encoding="utf-8")

    readme = out_dir / "README_run.md"
    readme.write_text(
        "\n".join(
            [
                "# Run guide",
                "",
                "1. Install Python deps: `pip install -r requirements.txt`",
                "2. Ensure ffmpeg/ffprobe are available in PATH.",
                "3. Run:",
                f"   `python -m voice_perfect --audio \"{input_audio.name}\" --script \"{script_path.name}\" --out \"{out_dir.name}\"`",
                "4. Execute generated ffmpeg command from script files if needed.",
                "",
                f"Fallback used: {fallback_used}",
            ]
        ),
        encoding="utf-8",
    )

    if args.run_ffmpeg:
        subprocess.run(ffmpeg_cmd, check=True)


if __name__ == "__main__":
    main()
