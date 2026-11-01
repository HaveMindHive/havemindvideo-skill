#!/usr/bin/env python3
"""Assemble a finished, edited video from shotlist.json with Remotion. No DaVinci Resolve needed.

Usage: python3 assemble.py path/to/shotlist.json [--music bed.mp3] [--music-volume 0.5] [--no-transcript]

Applies the basic rules from references/editing.md automatically:
  - Cut on the line: dead air before/after each spoken line is trimmed, keeping a
    small handle so no line starts mid-word (a line with no leading silence starts at frame 0).
  - Hard cuts inside a scene, an 8-frame dissolve where the shot's "scene" changes.
    The outgoing picture runs under the dissolve; its voice stops at the cut.
  - Every voice baked to -19 LUFS so lines sit at the same level.
  - One music bed, ducked under dialogue, up in silent shots, faded at both ends.
Optional per-shot keys in shotlist.json (break a rule on purpose):
  "scene": "kitchen"            dissolve when this changes between shots
  "transition_in": "cut" | "dissolve" | <frames>   override the default into this shot
  "trim": false                 keep the clip's full length (a held beat)
  "keep_level": true            don't level this voice (a whisper stays quiet)
Per shot it uses lipsync_file (its own audio), else video_file + optional audio_file.
Writes <shotlist dir>/final/<project>_v<N>.0_<MM-DD-YYYY>.mp4 (never overwrites), then runs
the final-pass checks: length, audio stream, black frames, loudness, contact sheet, and a
Whisper transcript checked against each shot's dialogue.
"""
import argparse, datetime, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEAD, TAIL = 0.20, 0.35  # seconds of handle kept before/after a line
DISSOLVE = 8  # frames, at scene changes
VOICE_LUFS = -19


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def seconds(path: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], check=True).stdout)


def has_audio(path: Path) -> bool:
    return bool(run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)]).stdout.strip())


def speech_span(path: Path) -> tuple[float, float]:
    """(first sound, last sound) in seconds, from ffmpeg silencedetect."""
    total = seconds(path)
    err = run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "silencedetect=noise=-35dB:d=0.15", "-f", "null", "-"]).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    first = ends[0] if starts and starts[0] < 0.05 and ends else 0.0
    last = starts[-1] if starts and (len(ends) < len(starts) or ends[-1] >= total - 0.05) else total
    return first, max(first, last)


def bake_voice(src: Path, dst: Path, level: bool):
    # ponytail: single-pass loudnorm, two-pass if lines still land >2 LU apart
    af = ["-af", f"loudnorm=I={VOICE_LUFS}:TP=-1.5:LRA=11"] if level else []
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vn", *af, "-ar", "48000", str(dst)], check=True)


def next_output(final_dir: Path, project: str) -> Path:
    date = datetime.date.today().strftime("%m-%d-%Y")
    name = re.sub(r"[^A-Za-z0-9-]+", "-", project).strip("-").lower() or "video"
    v = 1
    while (out := final_dir / f"{name}_v{v}.0_{date}.mp4").exists():
        v += 1
    return out


def plan(shotlist: dict, base: Path, assets: Path):
    fps = int(shotlist["fps"])
    shots, problems, notes = [], [], []
    for s in shotlist["shots"]:
        sid = s["id"]
        video = s.get("lipsync_file") or s.get("video_file")
        if not video or not (vpath := (base / video).resolve()).exists():
            problems.append(f"{sid}: video missing ({video})")
            continue
        vsec = seconds(vpath)
        if s.get("lipsync_file"):
            if not has_audio(vpath):
                problems.append(f"{sid}: lipsync_file has no audio stream (failed merge)")
                continue
            voice = vpath
        elif s.get("audio_file"):
            voice = (base / s["audio_file"]).resolve()
            if not voice.exists():
                problems.append(f"{sid}: audio missing ({s['audio_file']})")
                continue
        else:
            voice = None

        vname = f"{sid}{vpath.suffix}"  # fresh copy under the shot id every run (stale same-path rule)
        shutil.copy2(vpath, assets / vname)
        shot = {"id": sid, "video": f"assemble/{vname}", "video_in": 0, "frames": round(vsec * fps),
                "tail": 0, "fade_in": 0, "audio": None, "audio_in": 0, "dialogue": voice is not None,
                "_clip_frames": round(vsec * fps), "_scene": s.get("scene"), "_tin": s.get("transition_in")}

        if voice:
            aname = f"{sid}_vo.wav"
            bake_voice(voice, assets / aname, level=not s.get("keep_level"))
            shot["audio"] = f"assemble/{aname}"
            first, last = speech_span(voice)
            if s.get("trim", True):
                a_in = max(0.0, first - LEAD) if first > LEAD else 0.0
                a_out = min(seconds(voice), last + TAIL)
            else:
                a_in, a_out = 0.0, seconds(voice)
            length = a_out - a_in
            if voice == vpath:  # lipsync: picture and voice move together
                shot["video_in"] = shot["audio_in"] = round(a_in * fps)
            else:  # voice over b-roll: picture from 0, voice trimmed
                shot["audio_in"] = round(a_in * fps)
                if length > vsec + 0.05:
                    problems.append(f"{sid}: line runs {length:.2f}s but clip is {vsec:.2f}s, it would be cut off")
                    continue
            shot["frames"] = min(round(length * fps), shot["_clip_frames"] - shot["video_in"])
            cut = vsec - length
            if cut > 0.3:
                notes.append(f"{sid}: trimmed {cut:.1f}s of dead air")
        shots.append(shot)

    # Transitions: hard cut by default, dissolve where the scene changes, per-shot override wins.
    for prev, cur in zip(shots, shots[1:]):
        tin = cur["_tin"]
        if isinstance(tin, int):
            n = tin
        elif tin == "dissolve":
            n = DISSOLVE
        elif tin == "cut":
            n = 0
        else:
            n = DISSOLVE if prev["_scene"] and cur["_scene"] and prev["_scene"] != cur["_scene"] else 0
        spare = prev["_clip_frames"] - prev["video_in"] - prev["frames"]
        if n and spare < n:
            notes.append(f"{prev['id']} -> {cur['id']}: only {spare} spare frames for a {n}-frame dissolve, " +
                         ("shortened" if spare >= 3 else "hard cut instead"))
            n = spare if spare >= 3 else 0
        prev["tail"] = cur["fade_in"] = n

    for s in shots:
        for k in [k for k in s if k.startswith("_")]:
            del s[k]
    return {"fps": fps, "aspect_ratio": shotlist["aspect_ratio"], "shots": shots}, problems, notes


def final_checks(out: Path, props: dict, shotlist: dict, transcript: bool) -> bool:
    fps = props["fps"]
    want = sum(s["frames"] for s in props["shots"]) / fps
    got = seconds(out)
    audio = has_audio(out)
    print(f"\n{out}\n  length {got:.2f}s (expected {want:.2f}s), audio stream: {audio}")
    ok = abs(got - want) < 0.2 and audio

    err = run(["ffmpeg", "-hide_banner", "-i", str(out), "-vf", "blackdetect=d=0.25:pix_th=0.10", "-af", "ebur128", "-f", "null", "-"]).stderr
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)
    print("  black frames: " + (", ".join(f"{float(a):.2f}-{float(b):.2f}s" for a, b in blacks) or "none"))
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    print(f"  loudness: {lufs[-1] if lufs else '?'} LUFS integrated")

    sheet = out.with_suffix(".contact.png")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(out), "-vf", f"fps=1/2,scale=240:-1,tile=6x{max(1, -(-int(got // 2 + 1) // 6))}", "-frames:v", "1", str(sheet)])
    print(f"  contact sheet (1 frame / 2s, check continuity): {sheet}")

    lines = [(s["id"], s.get("dialogue")) for s in shotlist["shots"] if s.get("dialogue")]
    if transcript and lines and shutil.which("whisper"):
        run(["whisper", str(out), "--model", "medium", "--language", "en", "--output_format", "txt",
             "--output_dir", str(out.parent)])
        heard = set(re.findall(r"[a-z']+", out.with_suffix(".txt").read_text().lower())) if out.with_suffix(".txt").exists() else set()
        for sid, line in lines:
            words = re.findall(r"[a-z']+", line.lower())
            hit = sum(w in heard for w in words) / max(1, len(words))
            if hit < 0.7:
                print(f"  CHECK LINE {sid}: only {hit:.0%} of its words heard: \"{line}\"")
        print(f"  transcript: {out.with_suffix('.txt')}")
    elif lines:
        print("  transcript: skipped")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shotlist")
    ap.add_argument("--music")
    ap.add_argument("--music-volume", type=float, default=0.5)
    ap.add_argument("--no-transcript", action="store_true")
    a = ap.parse_args()

    sl_path = Path(a.shotlist).resolve()
    shotlist = json.loads(sl_path.read_text())
    assets = HERE / "public" / "assemble"
    shutil.rmtree(assets, ignore_errors=True)
    assets.mkdir(parents=True)

    props, problems, notes = plan(shotlist, sl_path.parent, assets)
    if problems:
        sys.exit("Not assembling, fix these shots first:\n  " + "\n  ".join(problems))
    if not props["shots"]:
        sys.exit("No shots to assemble.")
    for n in notes:
        print("edit:", n)

    props["music"], props["music_volume"] = None, a.music_volume
    if a.music:
        run(["ffmpeg", "-y", "-v", "error", "-i", a.music, "-vn", "-af", f"loudnorm=I={VOICE_LUFS}", "-ar", "48000",
             str(assets / "music.wav")], check=True)
        props["music"] = "assemble/music.wav"

    if not (HERE / "node_modules").exists():
        subprocess.run(["npm", "install"], cwd=HERE, check=True)

    final_dir = sl_path.parent / "final"
    final_dir.mkdir(exist_ok=True)
    out = next_output(final_dir, shotlist["project"])
    props_file = assets / "props.json"
    props_file.write_text(json.dumps(props, indent=2))
    subprocess.run(["npx", "remotion", "render", "src/index.ts", "Assemble", str(out),
                    f"--props={props_file}", "--codec=h264"], cwd=HERE, check=True)
    shutil.copy2(props_file, out.with_suffix(".edit.json"))  # what was cut, for the next pass

    if not final_checks(out, props, shotlist, not a.no_transcript):
        sys.exit("CHECK FAILED: length or audio is wrong, do not hand this off.")
    print("  OK. Watch it once, then open in CapCut for hand edits.")


if __name__ == "__main__":
    main()
