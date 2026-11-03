"""sync/lipsync-2-pro with hang protection (cancel + one retry).
usage: gen_lipsync2pro.py <out.mp4> <video.mp4> <audio.wav> [sync_mode cut_off]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replicate_job import run, data_uri, download
out, vid, aud = sys.argv[1:4]
inp = {"video": data_uri(vid), "audio": data_uri(aud), "sync_mode": sys.argv[4] if len(sys.argv) > 4 else "cut_off", "temperature": 0.3}
download(run("sync/lipsync-2-pro", inp, limit_s=int(os.environ.get("LIPSYNC_LIMIT_S", 420))), out)
