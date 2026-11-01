#!/usr/bin/env python3
"""Assemble a finished video from shotlist.json with Remotion. No DaVinci Resolve needed.

Usage: python3 assemble.py path/to/shotlist.json [--music bed.mp3] [--music-volume 0.25]

Per shot (in order) it uses lipsync_file, else video_file. If the shot has an
audio_file and no lipsync_file, the clip is muted and audio_file plays over it.
Shot length = the real clip length (ffprobe), not duration_s. Hard cuts.
Writes <shotlist dir>/final/<project>_v<N>.0_<MM-DD-YYYY>.mp4 (never overwrites),
then checks the file's real duration and that it has an audio stream.
"""
import argparse, datetime, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def probe_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def has_audio(path: Path) -> bool:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True).stdout.strip()
    return bool(out)


def next_output(final_dir: Path, project: str) -> Path:
    date = datetime.date.today().strftime("%m-%d-%Y")
    name = re.sub(r"[^A-Za-z0-9-]+", "-", project).strip("-").lower() or "video"
    v = 1
    while (out := final_dir / f"{name}_v{v}.0_{date}.mp4").exists():
        v += 1
    return out


def build_props(shotlist: dict, base: Path, assets: Path, music: Path | None, music_volume: float):
    fps = int(shotlist["fps"])
    shots, problems = [], []
    for s in shotlist["shots"]:
        video = s.get("lipsync_file") or s.get("video_file")
        if not video:
            problems.append(f"{s['id']}: no lipsync_file or video_file")
            continue
        vpath = (base / video).resolve()
        if not vpath.exists():
            problems.append(f"{s['id']}: missing {vpath}")
            continue
        audio = None if s.get("lipsync_file") else s.get("audio_file")
        apath = (base / audio).resolve() if audio else None
        if apath and not apath.exists():
            problems.append(f"{s['id']}: missing {apath}")
            continue
        vsec = probe_seconds(vpath)
        if apath and probe_seconds(apath) > vsec + 0.05:
            problems.append(f"{s['id']}: audio {probe_seconds(apath):.2f}s is longer than clip {vsec:.2f}s, the line would be cut off")
            continue
        # Fresh copy every run under the shot id (stale same-path media rule).
        vname = f"{s['id']}{vpath.suffix}"
        shutil.copy2(vpath, assets / vname)
        shot = {"id": s["id"], "video": f"assemble/{vname}", "audio": None, "frames": round(vsec * fps)}
        if apath:
            aname = f"{s['id']}_vo{apath.suffix}"
            shutil.copy2(apath, assets / aname)
            shot["audio"] = f"assemble/{aname}"
        shots.append(shot)
    props = {"fps": fps, "aspect_ratio": shotlist["aspect_ratio"], "shots": shots,
             "music": None, "music_volume": music_volume}
    if music:
        shutil.copy2(music, assets / f"music{music.suffix}")
        props["music"] = f"assemble/music{music.suffix}"
    return props, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shotlist")
    ap.add_argument("--music")
    ap.add_argument("--music-volume", type=float, default=0.25)
    a = ap.parse_args()

    sl_path = Path(a.shotlist).resolve()
    shotlist = json.loads(sl_path.read_text())
    music = Path(a.music).resolve() if a.music else None

    assets = HERE / "public" / "assemble"
    shutil.rmtree(assets, ignore_errors=True)
    assets.mkdir(parents=True)

    props, problems = build_props(shotlist, sl_path.parent, assets, music, a.music_volume)
    if problems:
        sys.exit("Not assembling, fix these shots first:\n  " + "\n  ".join(problems))
    if not props["shots"]:
        sys.exit("No shots to assemble.")

    if not (HERE / "node_modules").exists():
        subprocess.run(["npm", "install"], cwd=HERE, check=True)

    final_dir = sl_path.parent / "final"
    final_dir.mkdir(exist_ok=True)
    out = next_output(final_dir, shotlist["project"])
    props_file = assets / "props.json"
    props_file.write_text(json.dumps(props, indent=2))
    subprocess.run(["npx", "remotion", "render", "src/index.ts", "Assemble", str(out),
                    f"--props={props_file}", "--codec=h264"], cwd=HERE, check=True)

    # Verify the real file, not the render log.
    want = sum(s["frames"] for s in props["shots"]) / props["fps"]
    got = probe_seconds(out)
    ok = abs(got - want) < 0.2 and has_audio(out)
    print(f"\n{out}\n  length {got:.2f}s (expected {want:.2f}s), audio stream: {has_audio(out)}")
    if not ok:
        sys.exit("CHECK FAILED: length or audio is wrong, do not hand this off.")
    print("  OK, ready to open in CapCut.")


if __name__ == "__main__":
    main()
