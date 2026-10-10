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

## Path 2: Replicate, staying in one ecosystem

If your constraints keep you in Replicate for video, there are two shapes of model here — a one-call avatar model (recommended default) and a two-call bridge for when you already have a silent clip from elsewhere.

### 2a. One-call avatar + lipsync (recommended default for Replicate-only pipelines)

**`prunaai/p-video-avatar`** — takes a reference `image` plus **either** an uploaded `audio` file **or** a `voice_script` (text) + `voice` selection, and generates the synced talking video directly, in one call. This is the Replicate equivalent of ElevenLabs' Avatar workflow (Path 1) — it does identity + voice + lipsync together instead of requiring a separate silent-video generation step first. Confirmed live and working (verified against our own locked character portrait, 2026-10-09).

```python
import replicate

with open("character_portrait.png", "rb") as img, open("line.mp3", "rb") as audio:
    output = replicate.run("prunaai/p-video-avatar", input={
        "image": img,
        "audio": audio,          # use your own pre-generated voice line (e.g. from ElevenLabs)...
        "resolution": "1080p",   # "720p" or "1080p" — no explicit aspect_ratio field, infers from the image like kling
    })
```

Omit `audio` and set `voice_script` + `voice` instead to use its own built-in TTS — the `voice` enum (`"Zephyr (Female)"`, `"Puck (Male)"`, `"Kore (Female)"`, etc.) is literally Google's Gemini TTS voice set, so this model doubles as a Replicate-native bridge to the Google voice tier in `references/voices.md` without a separate Google API call. For a project that already generates lines through ElevenLabs for voice consistency across shots, pass the pre-generated `audio` file instead and ignore the built-in voice entirely. Health-check with `no_op: true` (still requires `image` and either `audio` or `voice_script` to pass schema validation, but skips the real inference) if you just want to confirm the endpoint/your inputs are valid before a real run.

This being a single call doesn't exempt it from the verification step below — check for an embedded audio stream in the output the same as any other path.

### 2b. Two-call bridge (silent video + separate audio merge)

Use this when you already have a silent clip from somewhere else (e.g. a kling clip generated specifically for its camera motion/action, where re-doing the whole shot through an avatar model would lose that) and just need to add sync to it:

- **`sync/lipsync-2-pro`**, inputs: `video` (uri), `audio` (uri, docs say `.wav` but other common formats generally work), `sync_mode` (default `"loop"`, handles a video/audio duration mismatch by looping the shorter of the two rather than failing), `temperature` (0-1, how expressive the lipsync can be), `active_speaker` (bool, intended to pick which face is speaking when several people are in frame). **Do not rely on it.** Tested on a two-shot with a silent second character: it animated the wrong person (the character who was NOT supposed to speak). See "Two-face shots" below.
- **`bytedance/latentsync`** — alternative, also solid quality.
- **`kwaivgi/kling-avatar-v2`** — Kling's own avatar/lipsync model, same model family as Kling video generation if you want to stay in one vendor's ecosystem.

All exist and work as of 2026-10-09 — but **Replicate model IDs and versions drift over time** (confirmed: two unrelated video models on Replicate were found pointing at deleted/stale versions within the same month). Before trusting a model id in any doc including this one, check the live schema:

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

## Path 3: self-hosted SadTalker

A fourth option if none of the above fit (cost control at scale, no third-party API dependency, or you already run your own GPU infra): **SadTalker**, self-hosted on your own GPU (Modal, RunPod, or local). Same underlying limitation as the hosted options — sync quality degrades past roughly a 30° turned face, so the front-facing framing advice below still applies regardless of which path you pick. Worth it mainly when generation volume is high enough that per-clip hosted-API cost matters more than setup effort; for occasional/low-volume work, Path 1 or 2 is less to maintain.

**A real alternative when lipsync precision genuinely doesn't matter for a shot**: skip lipsync entirely and use plain image-to-video motion (a character gesturing, reacting, moving naturally with mouth closed or only vaguely moving) for stylized characters, non-dialogue atmosphere beats, or brief cameo lines where the audience's attention is on something else in frame. Don't reach for this as a cost-cutting shortcut on a shot that's actually supposed to read as the character speaking a specific line — that's the exact mistake this doc exists to prevent — but it's a legitimate choice for a shot that was never going to need tight sync in the first place.

### Critical: verify the merge actually worked

**A lipsync job can return a file URL that looks successful but contains no audio.** Don't assume success just because you got a response — always check the output before trusting it:

```bash
ffprobe -v error -show_streams -select_streams a synced_clip.mp4
```

If that prints nothing, the merge silently failed (or produced a video-only file) and you have a silent clip, not a lip-synced one. Check this for every merged clip before it goes into the edit — a background batch job that "completes" is not the same as a batch job that *worked*.

### Two-face shots: keep dialogue single-face

Confirmed in production: `sync/lipsync-2-pro` on a two-person shot, with `active_speaker: true`, moved the mouth of the wrong character. The model only sees a silent video plus an audio file, so it has nothing reliable to decide which of two faces owns the line. Rules that avoid the whole problem:

- **Every line of dialogue gets a single-face shot** (a close-up or medium of the speaker, or an over-the-shoulder with only the speaker's face in frame). Generate it one call with `prunaai/p-video-avatar` from a reference image of just that character in that frame.
- **Keep two-shots for establishing shots and physical action** (a hand-off, a reaction). Putting dialogue on a two-shot is risky; only do it if you can isolate the speaker (for example by running lipsync on a crop containing only that face and compositing it back), and check the result.
- Cut between the single-face dialogue shots and the silent two-shot like a normal editor would.

### Very short audio fails

`prunaai/p-video-avatar` rejected a 0.64 s line with a server error (HTTP 500). Pad very short lines with a little silence before and after (about 0.3 s lead, 0.9 s tail, ending near 1.8 s total) and re-run.

### Avatar clips are longer than the audio

`prunaai/p-video-avatar` returns a clip a little longer than the audio you give it (about 0.3 to 0.9 s of trailing silence, and the video length is rounded up to whole seconds). The audio inside is byte-identical to your file (verified by cross-correlation), so nothing about the voice changes. Trim the tail in the edit (source end frame = audio length plus a few frames) rather than leaving dead air.

`video_prompt` on that model steers expression and action (for example "eyes closed, nodding slowly", "grins, not looking up"). Use it, and keep it consistent with the reference image. A reference image that already shows the right expression and framing matters more than the prompt.

### Known limitation

Lipsync models can glitch on a turned or profile face — the mouth sync degrades noticeably when the face isn't close to front-on. For any shot with real spoken dialogue, bias toward front-facing or near-front-facing framing; save profile/turned angles for reaction shots and non-dialogue beats.

## Decision tree

```
Does this shot have spoken dialogue that the audience needs to read as sync'd?
├── No / doesn't matter for this shot → any video model, no lipsync needed (motion-only is fine)
└── Yes → Can the project use ElevenLabs beyond plain TTS?
          ├── Yes → Avatar + Lip Sync workspace (Path 1)
          └── No, Replicate-only constraint
                 ├── Starting fresh, no silent video generated yet
                 │     → prunaai/p-video-avatar, one call (Path 2a)
                 ├── Already have a silent clip (generated for specific motion/camera work)
                 │     → lipsync bridge onto it (Path 2b)
                 └── High volume, cost/infra control matters → self-hosted
                       SadTalker (Path 3)
Every path: verify embedded audio stream on the output before trusting it.
```

## Other avatar services (not evaluated in depth)

**HeyGen** is another paid avatar/lipsync service (similar category to ElevenLabs' Avatar workflow) with several community Claude Code skill wrappers available. Not tested against this pipeline — worth knowing it exists as an alternative if ElevenLabs/Replicate don't fit a project's constraints, but no specific guidance here beyond that.
