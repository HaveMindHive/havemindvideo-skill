"""Kling 3.0 pro image-to-video with hang protection (cancel + one retry).
usage: gen_kling3.py <out.mp4> <start_image> '<prompt>' [duration 3-15] [mode pro] [end_image]
Negative prompt from $NEG. Before paying for this: start image checked (closed mouth for talking
shots, 5 fingers per hand, no extra people), duration = line length + ~1 s."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replicate_job import run, data_uri, download
out, img, prompt = sys.argv[1:4]
dur = int(sys.argv[4]) if len(sys.argv) > 4 else 5
inp = {"start_image": data_uri(img), "prompt": prompt, "duration": dur, "aspect_ratio": "9:16", "mode": "pro",
       "generate_audio": False,
       "negative_prompt": os.environ.get("NEG", "extra people, extra fingers, face morph, lighting change, camera movement, subtitles, text")}
if len(sys.argv) > 6 and sys.argv[6]:
    inp["end_image"] = data_uri(sys.argv[6])
download(run("kwaivgi/kling-v3-video", inp, limit_s=int(os.environ.get("KLING_LIMIT_S", 600))), out)
