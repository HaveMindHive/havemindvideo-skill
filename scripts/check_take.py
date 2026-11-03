#!/usr/bin/env python3
"""Check ONE take before anyone sees it. Free, local, ~20-40 s.

    python3 check_take.py <shotlist.json> <shot_id> <clip.mp4> [--frames 12]

Prints PASS/FAIL lines and writes a small (<=1024 px wide) contact sheet next to the clip:
<clip>.sheet.png. Look at that sheet (it's small enough to view) against the shot's numbered
checklist: same person, 5 fingers, no extra people, mouth/eyes per the direction, no jumps.

Checks done automatically:
- file plays, 9:16, duration vs the line length (+~1 s)
- dialogue shots: audio stream present, Whisper hears the line (word overlap >= 70%)
- sudden jumps: frame-to-frame change spikes (snaps into an end frame, glitches, cuts)
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def probe(p):
    r = sh("ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(p))
    return json.loads(r.stdout or "{}")


def words(t):
    return re.findall(r"[a-z']+", re.sub(r"\[[^\]]*\]", " ", (t or "").lower()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shotlist"); ap.add_argument("shot_id"); ap.add_argument("clip")
    ap.add_argument("--frames", type=int, default=12)
    a = ap.parse_args()
    root = Path(a.shotlist).resolve().parent
    shots = json.load(open(a.shotlist))["shots"]
    shot = next((s for s in shots if s["id"] == a.shot_id or s["id"] == f"shot{a.shot_id}"), None)
    if not shot:
        sys.exit(f"FAIL no shot {a.shot_id} in shotlist")
    clip = Path(a.clip) if Path(a.clip).is_absolute() else root / a.clip
    ok = True

    def res(good, msg):
        nonlocal ok
        ok &= good
        print(("PASS " if good else "FAIL ") + msg)

    info = probe(clip)
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not v:
        sys.exit("FAIL file has no video / doesn't play")
    dur = float(info.get("format", {}).get("duration", 0))
    res(abs(v["width"] / v["height"] - 9 / 16) < 0.03, f"aspect {v['width']}x{v['height']}")
    line = shot.get("dialogue")
    if line:
        has_a = any(s.get("codec_type") == "audio" for s in streams)
        res(has_a, "audio stream present" if has_a else "NO AUDIO: this is a silent acting clip, lip-sync it first")
        n = len(words(line))
        res(dur >= n / 2.8, f"duration {dur:.1f}s for {n} words")
        if has_a:
            with tempfile.TemporaryDirectory() as td:
                sh("whisper", str(clip), "--model", "base.en", "--language", "en", "--output_format", "txt", "--output_dir", td, "--fp16", "False")
                txt = next(Path(td).glob("*.txt"), None)
                heard = words(txt.read_text()) if txt else []
            want = words(line)
            hit = sum(1 for w in want if w in heard) / max(1, len(want))
            res(hit >= 0.7, f"Whisper heard {hit:.0%} of the line: \"{' '.join(heard)[:120]}\"")
    else:
        print(f"INFO no dialogue; duration {dur:.1f}s")

    # sudden jumps: mean abs difference between consecutive frames at 12 fps, small size
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", "fps=12,scale=96:-2,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    h = int(round(96 * v["height"] / v["width"] / 2) * 2)
    fs = 96 * h
    frames = [raw[i:i + fs] for i in range(0, len(raw) - fs + 1, fs)]
    diffs = [sum(abs(x - y) for x, y in zip(frames[i], frames[i + 1])) / fs for i in range(len(frames) - 1)]
    if diffs:
        med = sorted(diffs)[len(diffs) // 2] or 0.5
        spikes = [(i / 12, d) for i, d in enumerate(diffs) if d > max(4 * med, 6)]
        res(not spikes, "no sudden jumps" if not spikes else "JUMP at " + ", ".join(f"{t:.1f}s" for t, _ in spikes[:5]) + " (snap/glitch/cut: look at it)")
        # Expression "snaps" (a fast pose change into an end frame) are too close to normal motion
        # to auto-fail (Stop Swiping 13 v7 snap 2.5x vs approved v8 2.0x). Point the reviewer at it.
        w = [sum(diffs[i:i + 6]) for i in range(max(1, len(diffs) - 5))]
        wm = sorted(w)[len(w) // 2] or 0.5
        peak = max(range(len(w)), key=lambda i: w[i])
        print(f"LOOK fastest movement at {peak / 12:.1f}-{peak / 12 + 0.5:.1f}s ({w[peak] / wm:.1f}x typical"
              + ("; over 2.3x: check for a snap/jerk there" if w[peak] / wm > 2.3 else "") + ")")

    # small contact sheet to look at
    sheet = clip.with_suffix(".sheet.png")
    n = a.frames
    sh("ffmpeg", "-v", "error", "-y", "-i", str(clip), "-vf",
       f"fps={n / max(dur, 0.1):.4f},scale=256:-2,tile={min(n, 6)}x{(n + 5) // 6}", "-frames:v", "1", str(sheet))
    print(f"SHEET {sheet}  (view it; check the shot's numbered checklist)")
    print("RESULT", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
