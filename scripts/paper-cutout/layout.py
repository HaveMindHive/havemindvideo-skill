"""Layout script for a narration-only paper cut-out short. Drives EVERYTHING from shotlist.json + current audio.
A cut or retime is a one-line change here, then re-run. Writes:
  clips/conformed/*.mp4   1080x1920 24fps, stop-motion cadence, exact frame counts (name carries frame count)
  overlays/overlay_*.mov  transparent ProRes 4444 with paper lettering + captions
  edl.json                what to place in Resolve (record frames are RELATIVE to timeline start)
usage: python3 layout.py [audio_key]   audio_key = which audio file field to use (default: audio_file)
"""
import json, math, os, glob, subprocess, random, sys, re, hashlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FPS, W, H = 24, 1080, 1920
BREATH, LEAD, MINSHOT, DX, TAIL_END = 0.45, 0.10, 3.0, 8, 0.6   # seconds; DX = dissolve frames
DISSOLVE_AFTER = {"shot08", "shot16"}                  # soft beat changes: 8f dissolve on alternating tracks
WIPE_AFTER = {"shot05", "shot11", "shot14"}            # big beat changes: hard cut hidden under a torn paper wipe (fx.py)
WIPE_FRAMES = 16; WIPE_CUT = 8; ZOOM = 0.05; LAST_FADE = 14
CLIP_VERSION = {}            # override: {"shot05": 1}; default = highest version on disk
FONT = "/System/Library/Fonts/MarkerFelt.ttc"
man = json.load(open("shotlist.json"))
os.makedirs("clips/conformed", exist_ok=True); os.makedirs("overlays/states", exist_ok=True)

def probe(f, ent="format=duration"):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", ent, "-of", "csv=p=0", f]).decode().strip())

def latest(sid):
    v = CLIP_VERSION.get(sid)
    if v is None:
        v = max(int(re.search(r"_v(\d+)\.mp4", p).group(1)) for p in glob.glob(f"clips/{sid}_v*.mp4"))
    return f"clips/{sid}_v{v}.mp4"

# ---------- timing ----------
shots = man["shots"]
t = 0
for i, s in enumerate(shots):
    a = probe(s["audio_file"])
    d = max(MINSHOT, a + LEAD + BREATH + (TAIL_END if i == len(shots) - 1 else 0))
    s["_a"], s["_base"] = a, round(d * FPS)
    s["_extra"] = DX if s["id"] in DISSOLVE_AFTER else 0
    s["_rec"] = t; t += s["_base"]
TOTAL = t
print(f"total {TOTAL} frames = {TOTAL/FPS:.1f}s")

# ---------- conform clips ----------
for s in shots:
    src = latest(s["id"]); N = s["_base"] + s["_extra"]; need = N / FPS; L = probe(src)
    f = 1.0; hold = 0.0
    if need > L:
        f = min(need / L, 1.3); hold = max(0.0, need - L * f)
    n12 = max(1, N // 2); z = f"1+{ZOOM}*on/{n12}" if shots.index(s) % 2 == 0 else f"{1+ZOOM}-{ZOOM}*on/{n12}"
    vf = (f"scale=-2:{H}:flags=lanczos,crop={W}:{H},setpts={f:.4f}*PTS,fps=12,scale={W*2}:{H*2}:flags=bicubic,"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=12,fps={FPS}")
    if hold > 0: vf += f",tpad=stop_mode=clone:stop_duration={hold:.3f}"
    tag = hashlib.md5(f"{src}{N}{f:.3f}{vf}".encode()).hexdigest()[:6]
    out = f"clips/conformed/{s['id']}_{N}f_{tag}.mp4"
    if not os.path.exists(out):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", vf, "-frames:v", str(N), "-r", str(FPS),
                        "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", out], check=True)
    s["_clip"], s["_src"], s["_slow"], s["_hold"] = out, src, round(f, 2), round(hold, 2)
    print(s["id"], os.path.basename(src), f"{N}f", f"slow x{f:.2f}", f"hold {hold:.2f}s")

# ---------- tracks and fades ----------
tr = 1
for i, s in enumerate(shots):
    if i and shots[i - 1]["id"] in DISSOLVE_AFTER: tr = 2 if tr == 1 else 1
    s["_track"] = tr
idx = {1: 0, 2: 0}
for s in shots: s["_item_index"] = idx[s["_track"]]; idx[s["_track"]] += 1
fades = []
for i, s in enumerate(shots):
    if i and shots[i - 1]["id"] in DISSOLVE_AFTER:
        if s["_track"] == 2: fades.append({"shot": s["id"], "track": 2, "item_index": s["_item_index"], "FadeIn": DX})
        else:
            p = shots[i - 1]; fades.append({"shot": p["id"], "track": 2, "item_index": p["_item_index"], "FadeOut": DX})

# ---------- overlay art ----------
random.seed(7)
COL = [(196, 90, 52), (84, 168, 160), (226, 170, 52), (240, 232, 214)]
def font(sz): return ImageFont.truetype(FONT, sz)
def shadow(layer, off=(7, 10), blur=8, op=110):
    a = layer.split()[3].point(lambda v: int(v * op / 255)); sh = Image.new("RGBA", layer.size, (30, 20, 10, 0)); sh.putalpha(a)
    sh = sh.filter(ImageFilter.GaussianBlur(blur)); out = Image.new("RGBA", layer.size, (0, 0, 0, 0)); out.alpha_composite(sh, off); out.alpha_composite(layer); return out
def tag(text, size=54, fill=(244, 236, 216), ink=(58, 38, 28), maxw=900):
    f = font(size); words = text.split(); lines = [""]
    for w in words:
        if f.getlength((lines[-1] + " " + w).strip()) <= maxw: lines[-1] = (lines[-1] + " " + w).strip()
        else: lines.append(w)
    lh = int(size * 1.25); tw = max(int(f.getlength(l)) for l in lines); pad = 34
    w, h = tw + 2 * pad, lh * len(lines) + 2 * pad
    L = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    j = lambda: random.randint(-4, 4)
    d.polygon([(j(), j()), (w + j(), j()), (w + j(), h + j()), (j(), h + j())], fill=fill)
    for k, l in enumerate(lines): d.text((w // 2, pad + k * lh + lh // 2), l, font=f, fill=ink, anchor="mm")
    return L.rotate(random.uniform(-2.2, 2.2), expand=True, resample=Image.BICUBIC)
def ransom(text, tile=118):
    letters = [c for c in text]; gap = 12
    L = Image.new("RGBA", (len(letters) * (tile + gap) + 40, tile + 80), (0, 0, 0, 0)); x = 20
    for k, c in enumerate(letters):
        if c == " ": x += tile // 2; continue
        bg = COL[k % 3]; ink = (244, 236, 216) if bg != COL[3] else (58, 38, 28)
        T = Image.new("RGBA", (tile, tile + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(T)
        d.rectangle((0, 0, tile - 1, tile + 9), fill=bg); d.text((tile // 2, tile // 2 + 4), c, font=font(int(tile * 0.78)), fill=ink, anchor="mm")
        T = T.rotate(random.uniform(-7, 7), expand=True, resample=Image.BICUBIC); L.alpha_composite(T, (x, random.randint(10, 40))); x += tile + gap
    return L.crop(L.getbbox())
def place(canvas, layer, cx, cy):
    layer = shadow(layer); canvas.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))

# labels: shot -> list of (kind, text, cx, cy, start fraction of shot, ...). Words are NOT generated by the video model.
LABELS = {
 # shot id -> list of (kind, text, cx, cy, start_fraction_of_shot[, tile_size_or_font[, max_width]])
 #   kind "ransom": big paper-letter tiles for short words; kind "tag": cardstock tag for longer labels.
 # Example: "shot01": [("ransom", "WORD?", 540, 330, 0.10)],
}
FUNC = {"a","an","the","of","to","as","is","by","in","on","at","that","and","but","or","it","its","with","without","if","for","from","there's","how","so","this","one","your","my","who","whose"}
def split_chunks(txt, mx=7):
    """Phrase-aware caption chunks: sentences -> DP over words (2..mx per chunk), avoid ending on function words, prefer comma breaks."""
    out = []
    for sent in re.split(r"(?<=[.?!])\s+", txt.strip()):
        w = sent.split(); n = len(w)
        if n <= mx: out.append(sent); continue
        best = [(1e9, None)] * (n + 1); best[0] = (0, None)
        for j in range(1, n + 1):
            for i in range(max(0, j - mx), j):
                ln = j - i
                if ln < 2 and n > 1: continue
                last = re.sub(r"[^a-z']", "", w[j - 1].lower())
                c = (ln - 4) ** 2 + (6 if last in FUNC and j < n else 0) - (3 if w[j - 1].endswith(",") else 0)
                if best[i][0] + c < best[j][0]: best[j] = (best[i][0] + c, i)
        cuts = []; j = n
        while j > 0: i = best[j][1]; cuts.append((i, j)); j = i
        out += [" ".join(w[i:j]) for i, j in reversed(cuts)]
    return out

WORDS = {}
try: WORDS = json.load(open(f"audio/{man['voice']['tag']}_word_times.json"))
except Exception: pass
def chunk_times(sid, chunks, a):
    """start/end (seconds inside the audio clip) for each chunk, by character interpolation over Whisper word times."""
    ws = WORDS.get(sid)
    if not ws: 
        tw = sum(len(c.split()) for c in chunks); cur = 0; res = []
        for c in chunks: d = a * len(c.split()) / tw; res.append((cur, cur + d)); cur += d
        return res
    chars = [len(x["w"]) for x in ws]; tot = sum(chars); cum = [0]
    for c in chars: cum.append(cum[-1] + c)
    def at(frac, which):
        pos = frac * tot
        for k in range(len(ws)):
            if cum[k + 1] >= pos - 1e-9:
                span = chars[k]; f = (pos - cum[k]) / span if span else 0
                return ws[k]["s"] + f * (ws[k]["e"] - ws[k]["s"])
        return ws[-1]["e"]
    sc = [len(re.sub(r"[^A-Za-z0-9]", "", c)) for c in chunks]; st = sum(sc); res = []; acc = 0
    for k, c in enumerate(chunks):
        res.append((at(acc / st, "s"), at((acc + sc[k]) / st, "e"))); acc += sc[k]
    return res

events = []   # (start_s, end_s, kind, payload)
LABEL_T = []
for s in shots:
    t0 = s["_rec"] / FPS; end = (s["_rec"] + s["_base"]) / FPS
    for lb in LABELS.get(s["id"], []):
        kind, text, cx, cy, fr = lb[:5]; extra = lb[5] if len(lb) > 5 else None
        events.append((t0 + fr * (end - t0), end, kind, (text, cx, cy, extra, lb[6] if len(lb) > 6 else None))); LABEL_T.append(round(t0 + fr * (end - t0), 3))
    ch = split_chunks(s["narration"]); ct = chunk_times(s["id"], ch, s["_a"]); a0 = t0 + LEAD
    for k, c in enumerate(ch):
        st_ = a0 + ct[k][0] if k else t0 + LEAD * 0.5
        en_ = (a0 + ct[k + 1][0]) if k + 1 < len(ch) else min(end, a0 + s["_a"] + 0.35)
        events.append((st_, en_, "cap", (c,)))
cuts = sorted({0.0, TOTAL / FPS} | {round(e[0], 4) for e in events} | {round(e[1], 4) for e in events})
cuts = [c for c in cuts if 0 <= c <= TOTAL / FPS]
cache = {}; segs = []
def art(ev, memo={}):
    k = (ev[2], ev[3]);
    if k in memo: return memo[k]
    kind, (text, *rest) = ev[2], ev[3]
    if kind == "cap": layer = tag(text, size=58, maxw=880); pos = (540, 1520)
    elif kind == "ransom": layer = ransom(text, rest[2] or 118); pos = (rest[0], rest[1])
    else: layer = tag(text, size=rest[2] or 50, fill=(226, 170, 52), maxw=rest[3] or 900); pos = (rest[0], rest[1])
    memo[k] = (layer, pos); return memo[k]
for a, b in zip(cuts, cuts[1:]):
    if b - a < 1e-3: continue
    act = [e for e in events if e[0] - 1e-3 <= a and e[1] >= b - 1e-3]
    key = tuple(sorted((e[2], e[3]) for e in act))
    if key not in cache:
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for e in act:
            layer, (cx, cy) = art(e); place(cv, layer, cx, cy)
        p = f"overlays/states/state_{len(cache):03d}.png"; cv.save(p); cache[key] = p
    segs.append((cache[key], b - a))
with open("overlays/concat.txt", "w") as f:
    for p, d in segs: f.write(f"file '{os.path.abspath(p)}'\nduration {d:.4f}\n")
    f.write(f"file '{os.path.abspath(segs[-1][0])}'\n")
ov = f"overlays/overlay_{TOTAL}f_{hashlib.md5(open('overlays/concat.txt','rb').read()+b''.join(open(p,'rb').read() for p in sorted(cache.values()))).hexdigest()[:6]}.mov"
if not os.path.exists(ov):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "overlays/concat.txt", "-vf", f"fps={FPS},format=yuva444p10le",
                    "-frames:v", str(TOTAL), "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", ov], check=True)

# ---------- EDL ----------
wipes = [{"after": s["id"], "record_frame": shots[i + 1]["_rec"] - WIPE_CUT, "frames": WIPE_FRAMES, "clip": os.path.abspath("overlays/paper_wipe_16f.mov")}
         for i, s in enumerate(shots[:-1]) if s["id"] in WIPE_AFTER]
edl = {"fps": FPS, "total_frames": TOTAL, "overlay": os.path.abspath(ov), "fades": fades, "wipes": wipes, "last_fade": LAST_FADE, "label_times": LABEL_T, "shots": []}
for s in shots:
    edl["shots"].append({"id": s["id"], "clip": os.path.abspath(s["_clip"]), "frames": s["_base"] + s["_extra"], "record_frame": s["_rec"],
                         "track": s["_track"], "item_index": s["_item_index"], "audio": os.path.abspath(s["audio_file"]),
                         "audio_record_frame": s["_rec"] + round(LEAD * FPS), "audio_s": round(s["_a"], 2), "narration": s["narration"]})
json.dump(edl, open("edl.json", "w"), indent=2)
print("overlay", ov, "| segments", len(segs), "| fades", len(fades), "| wipes", len(wipes))
