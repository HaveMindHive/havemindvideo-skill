#!/usr/bin/env python3
"""
QA check for HAVEMINDVIDEO shot list manifests.

Verifies the ACTUAL generated files against the manifest's expectations —
aspect ratio, duration, and (for lipsynced shots) that an audio stream is
really embedded — and updates each shot's status fields in place. This is
the automated half of references/self-check.md; it catches the class of
failure where an API call "succeeded" but the file it produced is wrong.

It does not look at frame content (wrong character, garbled text) — that
still needs a human or a vision-capable check, see references/self-check.md.

Usage:
    python3 qa_check.py shotlist.json
    python3 qa_check.py shotlist.json --fix-status   # write results back to the file
"""

import argparse
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def ffprobe_video(path: Path) -> dict | None:
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,avg_frame_rate",
                "-show_entries", "format=duration",
                "-of", "json", str(path),
            ],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    data = json.loads(out.stdout)
    if not data.get("streams"):
        return None
    stream = data["streams"][0]
    fmt = data.get("format", {})
    fps = None
    if stream.get("avg_frame_rate") and stream["avg_frame_rate"] != "0/0":
        fps = float(Fraction(stream["avg_frame_rate"]))
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "fps": fps,
        "duration_s": float(fmt["duration"]) if fmt.get("duration") else None,
    }


def has_audio_stream(path: Path) -> bool:
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "a",
                "-show_entries", "stream=index", "-of", "json", str(path),
            ],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    data = json.loads(out.stdout)
    return bool(data.get("streams"))


def expected_dims(aspect_ratio: str) -> tuple[int, int] | None:
    # width, height — loose match, not exact pixel count (models vary slightly)
    table = {"9:16": (9, 16), "16:9": (16, 9), "1:1": (1, 1)}
    return table.get(aspect_ratio)


def aspect_matches(width: int, height: int, aspect_ratio: str, tolerance: float = 0.08) -> bool:
    ratio_wh = expected_dims(aspect_ratio)
    if not ratio_wh:
        return True  # unknown target ratio, don't fail on it
    expected = ratio_wh[0] / ratio_wh[1]
    actual = width / height
    return abs(actual - expected) / expected <= tolerance


def check_shot(shot: dict, project_dir: Path, aspect_ratio: str) -> list[str]:
    problems = []
    shot_id = shot.get("id", "?")

    video_file = shot.get("video_file")
    if video_file:
        vpath = project_dir / video_file
        if not vpath.exists():
            problems.append(f"{shot_id}: video_file listed but not found at {vpath}")
            shot["video_status"] = "qa_failed"
        else:
            info = ffprobe_video(vpath)
            if info is None:
                problems.append(f"{shot_id}: video_file exists but ffprobe couldn't read it (corrupt or wrong codec)")
                shot["video_status"] = "qa_failed"
            else:
                ok = True
                if info["width"] and info["height"] and not aspect_matches(info["width"], info["height"], aspect_ratio):
                    problems.append(
                        f"{shot_id}: aspect ratio mismatch — got {info['width']}x{info['height']}, "
                        f"expected ~{aspect_ratio}"
                    )
                    ok = False
                expected_dur = shot.get("duration_s")
                if expected_dur and info["duration_s"] and abs(info["duration_s"] - expected_dur) > expected_dur * 0.5:
                    problems.append(
                        f"{shot_id}: duration way off — got {info['duration_s']:.1f}s, expected ~{expected_dur}s"
                    )
                    ok = False
                shot["video_status"] = "qa_passed" if ok else "qa_failed"

    lipsync_file = shot.get("lipsync_file")
    if lipsync_file and shot.get("dialogue"):
        lpath = project_dir / lipsync_file
        if not lpath.exists():
            problems.append(f"{shot_id}: lipsync_file listed but not found at {lpath}")
            shot["lipsync_status"] = "failed"
        elif not has_audio_stream(lpath):
            problems.append(
                f"{shot_id}: lipsync_file has NO embedded audio stream — merge likely failed silently"
            )
            shot["lipsync_status"] = "failed"
        else:
            shot["lipsync_status"] = "verified"

    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--fix-status", action="store_true",
                     help="write updated status fields back into the manifest file")
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text())
    project_dir = args.manifest.parent
    aspect_ratio = manifest.get("aspect_ratio", "9:16")

    all_problems = []
    for shot in manifest.get("shots", []):
        all_problems.extend(check_shot(shot, project_dir, aspect_ratio))

    if all_problems:
        print(f"QA found {len(all_problems)} problem(s):\n")
        for p in all_problems:
            print(f"  ✗ {p}")
    else:
        print("QA clean — no problems found in any shot with a generated file.")

    if args.fix_status:
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"\nStatus fields updated in {args.manifest}")

    sys.exit(1 if all_problems else 0)


if __name__ == "__main__":
    main()
