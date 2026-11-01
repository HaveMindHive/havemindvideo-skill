"""Bake the sound bed from edl.json: music (ducked under narration) + paper whooshes at wipes + thumps at lettering.
usage: python3 bed.py   -> audio/bed_<hash>.wav (48k stereo, full timeline length). Re-run after any retime/voice swap."""
import json, subprocess, hashlib, numpy as np, os
SR = 48000
e = json.load(open("edl.json")); FPS = e["fps"]; T = e["total_frames"] / FPS + 0.5
n = int(T * SR); rng = np.random.default_rng(3)

# music: 30s stereo @32k -> 48k, loop with 2s crossfades, trim
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "audio/music_bed_raw_v1.wav", "-ar", str(SR), "-ac", "2", "/tmp/m48.wav"], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "/tmp/m48.wav", "-i", "/tmp/m48.wav", "-i", "/tmp/m48.wav", "-i", "/tmp/m48.wav", "-filter_complex",
                "[0][1]acrossfade=d=2[a];[a][2]acrossfade=d=2[b];[b][3]acrossfade=d=2", "-f", "f32le", "-ac", "2", "/tmp/mloop.raw"], check=True)
mus = np.fromfile("/tmp/mloop.raw", np.float32).reshape(-1, 2)
mus = np.vstack([mus, mus]) if len(mus) < n else mus
mus = mus[:n]; mus = mus / (np.sqrt((mus ** 2).mean()) + 1e-9) * 10 ** (-26 / 20)      # base RMS -26 dBFS

# duck curve: -8 dB under narration, 120ms ramps; fade in 1s, out 3s
g = np.ones(n, np.float32)
for s in e["shots"]:
    a0 = int((s["audio_record_frame"] / FPS) * SR); a1 = a0 + int(s["audio_s"] * SR); g[a0:a1] = 10 ** (-8 / 20)
k = int(0.12 * SR); g = np.convolve(g, np.ones(k) / k, mode="same")
g *= np.clip(np.arange(n) / SR / 1.0, 0, 1) ** 1.5
g *= np.clip((T - np.arange(n) / SR) / 3.0, 0, 1)
mix = mus * g[:, None]

def add(sig, t0, gain_db):
    i = int(t0 * SR); m = sig * 10 ** (gain_db / 20); j = min(n, i + len(m))
    if i < n: mix[i:j] += m[:j - i, None] if m.ndim == 1 else m[:j - i]
def whoosh(dur=0.7):
    x = rng.normal(0, 1, int(dur * SR)).astype(np.float32); t = np.linspace(0, 1, len(x))
    # moving band: lowpass sweep via cumulative smoothing windows (cheap): blend of two smoothed noises
    s1 = np.convolve(x, np.ones(40) / 40, mode="same"); s2 = np.convolve(x, np.ones(6) / 6, mode="same")
    y = s1 * (1 - t) + s2 * t * 0.6
    env = np.sin(np.pi * t) ** 2; return (y * env / (np.abs(y * env).max() + 1e-9)).astype(np.float32)
def thump(dur=0.28):
    t = np.arange(int(dur * SR)) / SR; f = 110 * np.exp(-t * 9) + 55
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16); y += rng.normal(0, 0.35, len(t)) * np.exp(-t * 90)
    return (y / np.abs(y).max()).astype(np.float32)
W, TH = whoosh(), thump()
for w in e["wipes"]: add(W, (w["record_frame"] + 1) / FPS, -17)
for t in e["label_times"]: add(TH, t, -19)
# dissolves: very soft paper rustle
for f in e["fades"]: add(whoosh(0.5) * 0.5, 0.0 + (next(s["record_frame"] for s in e["shots"] if s["id"] == f["shot"]) - (0 if "FadeIn" in f else 8)) / FPS, -27)
pk = np.abs(mix).max(); mix = mix / pk * min(1.0, 0.7 / pk * pk) if pk > 0.9 else mix
out = f"audio/bed_{hashlib.md5(mix[::97].tobytes()).hexdigest()[:6]}.wav"
mix.astype(np.float32).tofile("/tmp/bed.raw")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "/tmp/bed.raw", "-c:a", "pcm_s16le", out], check=True)
d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out]).decode())
print(out, round(d, 2), "s", "peak", round(float(np.abs(mix).max()), 3))
e["bed"] = os.path.abspath(out); e["bed_s"] = round(d, 2); json.dump(e, open("edl.json", "w"), indent=2)
