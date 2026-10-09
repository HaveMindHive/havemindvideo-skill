# Lipsync — Getting Real Synced Dialogue

**Read this before generating any shot with spoken dialogue.** Getting this wrong is the single most expensive mistake in AI video production — it means regenerating every dialogue shot after the fact.

## The core fact

**Video-generation models like Kling do NOT produce real lipsync.** Prompting a video model with something like:

```
"...lips moving as if saying 'Close your eyes, dear.'"
```

only produces generic, unsynced mouth movement. It looks like talking, but it is never actually matched to a specific audio track's phonemes or timing — confirmed by direct side-by-side comparison against a real lipsync pass. No amount of prompt tuning fixes this; it's a capability gap in the underlying model, not a prompting problem. If a shot has dialogue, plan for one of the two paths below *before* generating it, not after.

## Path 1 (preferred): ElevenLabs Avatar + Lip Sync workspace

If your pipeline can use ElevenLabs beyond plain TTS, this is the best path — it generates voice, lipsync, and video together in one integrated step, which is structurally a much easier problem than bridging a silent video to a separate audio file after the fact.

Where: `elevenlabs.io/app/image-video` → Explore tab → **Lip sync** in the compose bar. (Not the same as a Studio project's own "Create → Video" panel, which is a generic video generator with no voice/lipsync pairing — don't use that for character dialogue.)

Core objects:
- **Avatar**: a character identity, created once from 3-5 reference images (or a text prompt). Has a default voice. Reused across the whole project.
- **Style**: a saved variant of an Avatar — different angle, outfit, lighting, or **pose**. Each Style is itself a static reference image anchoring both identity and composition.
- **Speech**: a Text-to-Speech generation (voice + text, same expressive tags as the plain API — `[whispers]`, `[laughs]`, etc. — work on v4+ voices).

Workflow per dialogue clip:
1. Avatar field → select the character → select a Style.
2. Speech field → "Text to Speech" → check History first for an existing take of that exact line (saves credits) → attach it.
3. Guide prompt (optional) — use it **only** for small deviations from the Style's reference image (a lighting tweak, minor angle change, subtle expression change).
4. Submit.

Gotchas that cost real time/credits if missed:
- **Submit before navigating anywhere else.** Clicking to another tab (e.g. Explore → History) while the compose panel still has Avatar/Speech/Prompt filled in **silently resets the whole panel** — nothing gets submitted, no error shown. Fill everything in, click submit, confirm it shows a spinner, *then* navigate.
- **A big pose change needs a new Style with a matching reference image, not a prompt override.** Don't try to talk the model into "sitting → laying down" or "facing camera → turned away" via the Guide prompt on a mismatched Style — it produces worse results than starting from a Style whose reference image already shows the target pose. Make the new Style first.
- Generation can take several minutes during busy periods — that's normal, not a failure; check History to see it land rather than assuming it's stuck.
- Two-person shots (wide two-shots, over-the-shoulder) don't fit the single-Avatar Lip Sync flow — it's built for one speaking face at a time. For a two-shot, generate a "together" reference image and feed it to the generic video generator instead, or use solo lip-synced inserts cut together with a silent establishing two-shot.

## Path 2: Replicate lipsync bridge (for Replicate-only pipelines)

If your constraints keep you in Replicate for video (silent clip already generated) plus a separate audio file (from the ElevenLabs API, Google TTS, or local TTS), merge them with a dedicated lipsync model:

- **`sync/lipsync-2-pro`** — inputs: `video` (uri), `audio` (uri, docs say `.wav` but other common formats generally work), `sync_mode` (default `"loop"` — handles a video/audio duration mismatch by looping the shorter of the two rather than failing), `temperature` (0-1, how expressive the lipsync can be), `active_speaker` (bool, auto-detects which face is actually speaking when multiple people are in frame — turn this on for any two-shot with one speaking character).
- **`bytedance/latentsync`** — alternative, also solid quality.
- **`kwaivgi/kling-avatar-v2`** — Kling's own avatar/lipsync model, same model family as Kling video generation if you want to stay in one vendor's ecosystem.

All three exist and work as of 2026-10-09 — but **Replicate model IDs and versions drift over time** (confirmed: two unrelated video models on Replicate were found pointing at deleted/stale versions within the same month). Before trusting a model id in any doc including this one, check the live schema:

```python
import replicate
m = replicate.models.get("sync/lipsync-2-pro")
print(m.latest_version.openapi_schema["components"]["schemas"]["Input"]["properties"])
```

```python
import replicate, requests

with open("silent_clip.mp4", "rb") as vf, open("line.mp3", "rb") as af:
    output = replicate.run("sync/lipsync-2-pro", input={
        "video": vf,
        "audio": af,
        "sync_mode": "loop",
        "active_speaker": True,
    })

r = requests.get(str(output))
r.raise_for_status()
open("synced_clip.mp4", "wb").write(r.content)
```

Pass local files as **open file handles**, not base64-encoded data URIs — embedding a video and an audio file as base64 in one JSON payload can bloat the request past a client-side read timeout. File handles let the SDK upload them and substitute a URL, which is both more reliable and avoids the payload-size problem entirely.

### Critical: verify the merge actually worked

**A lipsync job can return a file URL that looks successful but contains no audio.** Don't assume success just because you got a response — always check the output before trusting it:

```bash
ffprobe -v error -show_streams -select_streams a synced_clip.mp4
```

If that prints nothing, the merge silently failed (or produced a video-only file) and you have a silent clip, not a lip-synced one. Check this for every merged clip before it goes into the edit — a background batch job that "completes" is not the same as a batch job that *worked*.

### Known limitation

Lipsync models can glitch on a turned or profile face — the mouth sync degrades noticeably when the face isn't close to front-on. For any shot with real spoken dialogue, bias toward front-facing or near-front-facing framing; save profile/turned angles for reaction shots and non-dialogue beats.

## Decision tree

```
Does this shot have spoken dialogue?
├── No  → any video model, no lipsync needed
└── Yes → Can the project use ElevenLabs beyond plain TTS?
          ├── Yes → Avatar + Lip Sync workspace (Path 1)
          └── No, Replicate-only constraint, or audio already generated elsewhere
                 → generate silent video + audio separately, then
                   Replicate lipsync bridge (Path 2) — verify embedded
                   audio stream on every output before trusting it
```
