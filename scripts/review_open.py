#!/usr/bin/env python3
"""Open a take for review in QuickTime, labeled with its shot, but ONLY if it is reviewable.

Usage: python3 review_open.py <shotlist.json> <shot_id> <clip.mp4> [label words...]

Refuses (exit 1, says why) when:
  - the shot has dialogue and the clip has no audio stream (a silent acting base or a failed
    lip-sync merge is not a take; finish the lip-sync first),
  - the clip is missing or unreadable.
Otherwise copies it to <project>/review/SHOT <nn> - <line or action> - <label>.mp4 and opens it.
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

def probe(path, sel):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries",
                        "stream=index", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return bool(r.stdout.strip())

def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    sl, sid, clip = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    label = " ".join(sys.argv[4:]) or clip.stem
    shots = {s["id"]: s for s in json.loads(sl.read_text())["shots"]}
    if sid not in shots:
        sys.exit(f"NOT OPENED: no shot {sid} in {sl}")
    shot = shots[sid]
    if not clip.exists() or not probe(clip, "v"):
        sys.exit(f"NOT OPENED: {clip} is missing or has no video")
    if shot.get("dialogue") and not probe(clip, "a"):
        sys.exit(f"NOT OPENED: {sid} has a spoken line but {clip.name} has NO SOUND. "
                 "It is a silent acting base or a failed merge. Lip-sync it (and verify the audio "
                 "stream) before showing it to anyone.")
    words = re.sub(r"\[[^\]]*\]", "", shot.get("dialogue") or shot.get("action") or "").strip()
    words = re.sub(r"[^\w' ,.!?-]", "", words)[:50].strip()
    num = re.sub(r"^shot", "", sid)
    review = sl.parent / "review"
    review.mkdir(exist_ok=True)
    out = review / f"SHOT {num} - {words} - {label}.mp4"
    shutil.copy2(clip, out)
    subprocess.run(["open", "-a", "QuickTime Player", str(out)])
    print(f"OPENED: {out.name}")

if __name__ == "__main__":
    main()
