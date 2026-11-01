"""Narration per shot: ElevenLabs v3 preset voice via Replicate -> Whisper-verify (retry up to 4 takes) -> trim + loudnorm -> word times.
usage: python3 gen_vo.py [voice] [speed]   outputs audio/{id}_{tag}_v1.wav (mono 48k -18 LUFS) + audio/{tag}_word_times.json"""
import json, sys, subprocess, requests, os, re, concurrent.futures as cf, replicate, whisper
VOICE = sys.argv[1] if len(sys.argv) > 1 else "Bradford"; SPEED = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
tag = f"{VOICE.lower()}{int(SPEED*100)}"
man = json.load(open("shotlist.json")); shots = man["shots"]
v = replicate.models.get("elevenlabs/v3").latest_version; ref = f"elevenlabs/v3:{v.id}"
wm = whisper.load_model("medium")
def norm(s):
    s = s.lower().replace("-", " ").replace("'s ", " is ").replace("else's", "else is")
    s = re.sub(r"[^a-z0-9 ]", "", s).split()
    return ["c" if w == "see" else w for w in s]
def take(s, k):
    raw = f"audio/{s['id']}_{tag}_raw{k}.mp3"
    if not os.path.exists(raw):
        out = replicate.run(ref, input={"prompt": s["narration"], "voice": VOICE, "speed": SPEED}); url = str(out[0]) if isinstance(out, list) else str(out)
        open(raw, "wb").write(requests.get(url).content)
    return raw
def check(raw, s):
    r = wm.transcribe(raw, language="en", fp16=False, condition_on_previous_text=False)
    return norm(r["text"]) == norm(s["narration"]), r["text"].strip()
chosen = {}
words = json.load(open(f"audio/{tag}_word_times.json")) if os.path.exists(f"audio/{tag}_word_times.json") else {}
need = [i for i, s in enumerate(shots) if not (s.get("audio_file") and os.path.exists(s["audio_file"]) and s["id"] in words)]
print("regenerating", [shots[i]["id"] for i in need])
def work(i):
    s = shots[i]; log = []
    for k in range(1, 5):
        raw = take(s, k); ok, heard = check(raw, s); log.append((k, ok, heard))
        if ok: return i, raw, log
    return i, None, log
# generate sequentially in the whisper step (model not thread-safe); pre-generate first takes in parallel
with cf.ThreadPoolExecutor(4) as ex: list(ex.map(lambda i: take(shots[i], 1), need))
for i in need:
    i, raw, log = work(i); s = shots[i]
    if raw is None: print("NO CLEAN TAKE", s["id"], log); raw = take(s, 1)
    elif log[-1][0] > 1: print(s["id"], "needed take", log[-1][0])
    out = f"audio/{s['id']}_{tag}_v1.wav"
    af = ("silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.04,areverse,"
          "silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.12,areverse,loudnorm=I=-18:TP=-1.5:LRA=7")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", af, "-ac", "1", "-ar", "48000", out], check=True)
    r = wm.transcribe(out, language="en", word_timestamps=True, fp16=False, condition_on_previous_text=False)
    words[s["id"]] = [{"w": w["word"].strip(), "s": round(float(w["start"]), 3), "e": round(float(w["end"]), 3)} for sg in r["segments"] for w in sg["words"]]
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out]).decode())
    s["audio_raw"] = raw; s["audio_file"] = out; s["audio_s"] = round(d, 2); print(s["id"], round(d, 2), "s")
man["voice"] = {"status": f"APPROVED by the user: ElevenLabs v3 preset '{VOICE}' via Replicate, speed {SPEED}, default stability/similarity", "voice": VOICE, "speed": SPEED, "tag": tag}
json.dump(man, open("shotlist.json", "w"), indent=2); json.dump(words, open(f"audio/{tag}_word_times.json", "w"))
print("total narration", round(sum(s["audio_s"] for s in shots), 1), "s")
