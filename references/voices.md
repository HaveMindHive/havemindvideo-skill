# Voices — TTS Generation Options

Three tiers: paid cloud (ElevenLabs), paid cloud fallback (Google), free local (Chatterbox/Bark). Pick based on budget, voice-library needs, and whether contributors have API keys.

## 1. ElevenLabs API (TTS only — not the Avatar/Lip Sync workspace)

This is pure text-to-speech. For actual lip-synced video generation, see `lipsync.md` — that's a different, separate ElevenLabs product (their Image & Video / Avatar workspace), not this API.

### Generate speech

```bash
curl -X POST "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Close your eyes, dear. The energy flows better that way.",
    "model_id": "eleven_v3"
  }' \
  --output line.mp3
```

```python
import requests, os

def tts(voice_id: str, text: str, out_path: str):
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"},
        json={"text": text, "model_id": "eleven_v3"},
    )
    r.raise_for_status()
    open(out_path, "wb").write(r.content)
```

`model_id: "eleven_v3"` supports inline expressive **audio tags** right in the text — the model reads them as delivery direction, not literal words:

```
"[whispers] Are you awake?"
"[eyes snap open, startled, confused] Yes, yes, yes... wait a minute..."
"[hesitant] Yes... yes."
```

Tags like `[whispers]`, `[laughs]`, `[sighs]`, `[hesitant]`, `[confused]`, or a short parenthetical stage direction all work — the model is tolerant of plain-English direction, not just a fixed tag vocabulary.

### Picking a voice

Two endpoints, two different pools:

- `GET /v2/voices` (`xi-api-key` header, optional `page_size` up to ~100) — **your own saved "My Voices"** list only. Small (dozens, not thousands).
- `GET /v1/shared-voices?search=<term>&page_size=<n>` — the **full public shared library**. Much bigger, but the search is literal/keyword-ish, not semantic:
  - Short, specific nouns work: `"grandmother"`, `"witch"`, `"storyteller"`, `"fortune teller"` all return real hits.
  - Long descriptive phrases return **zero results**: `"nervous excited young woman casual"` or `"exotic older woman"` come back empty even though plenty of matching voices exist in the library. Search like a 2010s product-search box, not a chatbot.
  - A shared-library voice doesn't need to be "added" to your account first — you can call `/v1/text-to-speech/{voice_id}` directly with its id.

```python
r = requests.get(
    "https://api.elevenlabs.io/v1/shared-voices",
    headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
    params={"search": "fortune teller", "page_size": 10},
)
for v in r.json()["voices"]:
    print(v["voice_id"], v["name"], v.get("age"), v.get("accent"), v.get("description"))
```

### Auditioning candidates — use the real line, not a throwaway

When comparing 2-4 candidate voices for a character, generate the **actual target line with its real emotional direction**, not a flat neutral sentence. A generic "hello, this is a test" tells you almost nothing about whether a voice can land confusion, surprise, sarcasm, or a specific accent/age read. If the beat is "stunned disbelief," write the audition line with `[startled, confused]` and the real dialogue — otherwise you'll pick a voice that sounds fine reading a test sentence and falls flat on the actual performance.

## 2. Google voices (fallback) — **unverified, confirm before relying on this**

Not used or tested in this project yet. Two Google options exist and either could work as an ElevenLabs alternative/fallback:

- **Google Cloud Text-to-Speech API** — REST endpoint `POST https://texttospeech.googleapis.com/v1/text:synthesize`, auth via a service-account key or API key, request body takes `input.text` (or `input.ssml`), `voice.languageCode` + `voice.name`, `audioConfig.audioEncoding`. Supports WaveNet/Neural2/Studio voice tiers with varying expressiveness.
- **Gemini API's native TTS** (`gemini-2.5-flash-preview-tts` or similar, check current model name) — single-speaker and multi-speaker generation via the standard Gemini `generateContent` call with an audio response modality.

**Before trusting either**: verify the current endpoint, auth flow, exact field names, and voice list against Google's live docs — API shapes and model names here are confirmed to drift, and neither path has been exercised in this project. Treat this section as a starting pointer, not a tested recipe.

## 3. Local / free fallback: Chatterbox TTS + Bark

Zero API cost, runs on-device. Good default when a contributor has no API keys yet, or for drafting/scratch takes before spending paid-API budget on a final version.

**Chatterbox TTS** (Resemble AI, MIT licensed, production-grade):
- Voice cloning from ~6-30 seconds of clean reference audio (no background noise/music, consistent tone).
- Emotion/expressiveness slider (0.0 monotone → 1.0 very expressive).
- 23 languages.
- Benchmarked ahead of ElevenLabs in blind preference tests at release (worth re-verifying against current ElevenLabs models, but the underlying model is genuinely strong, not a toy).

```bash
python voice_studio.py --text "The tides roll in over the marsh." --output out.wav
python voice_studio.py --text "I sound like you now" --voice reference.wav --output cloned.wav
python voice_studio.py --text "This is incredible!" --emotion 0.9 --output excited.wav
```

**Bark** (Suno AI): expressive, supports inline tokens the model actually performs — `[laughs]`, `[sighs]`, `[music]` — and can sing short lines (`♪ lyrics here ♪`). 13 languages. Good for dramatic/comedic beats Chatterbox's emotion slider doesn't quite reach.

```bash
python voice_studio.py --engine bark --text "[laughs] Oh my, that's wonderful!" --output laugh.wav
```

Both run through the same local script/environment — swap `--engine chatterbox|bark`, no network call either way.

## Decision guide

| Situation | Use |
|---|---|
| Final, polished voice; existing ElevenLabs voice library; budget for API calls | **ElevenLabs** |
| No ElevenLabs access, need a paid fallback | **Google Cloud TTS / Gemini TTS** (verify API shape first — see above) |
| No API keys at all, drafting/scratch takes, need voice cloning from your own sample, zero cost | **Chatterbox / Bark (local)** |
