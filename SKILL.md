---
name: havemindvideo
description: Produce a finished, lip-synced, multi-character video ad or short from a script — Replicate for images/video, ElevenLabs/Google/local for voice, DaVinci Resolve for assembly. Use when asked to make an AI video, ad, or short-form clip with consistent characters and real dialogue, not just a single one-off generation.
---

# HAVEMINDVIDEO

An end-to-end pipeline skill for turning a script into a finished video: locked character identities, real synced dialogue, assembled in DaVinci Resolve. Built after a session that burned real API spend on exactly the mistakes this skill now prevents — see `references/character-consistency.md` and `references/lipsync.md` for the specific failures that shaped this design.

**The one rule that matters most: never reuse a generic reference image across unrelated shots, and never trust a generation without checking it before building on it.** Everything else below exists to enforce that rule automatically instead of relying on remembering it.

## Hard-won rules (added after a 16-shot production)

1. **One reference image per frame**, describing the scene and the framing, plus a scene reference so the set stays consistent. See `references/character-consistency.md`.
2. **Confirm voices with the user** before generating a whole script; build an audition page. Never take a handoff note's word for which voice was chosen. See `references/voices.md`.
3. **Prefer single-face dialogue shots.** Lipsync on a two-person frame can animate the wrong person; `active_speaker` does not reliably fix it. See `references/lipsync.md`.
4. **Review contact sheets, not first frames**, and pilot one shot of each type before batching the rest. See `references/self-check.md`.
5. **Scope fixes to the scene that has the problem.** A note about one shot is not a verdict on the whole character, voice, or approach; keep what works, reuse approved assets, and redo only what changed.
6. **Update the manifest and these docs as you learn things.** A skill that still describes a failed approach as working is worse than none.

7. **Edit passes do only the precise thing asked.** When the user says "cut this clip", cut that clip and nothing else, then render. Audio levels and transitions are a separate pass the user will request. Never improvise extra fades, dissolves, trims, or mix changes inside a cut pass. Keep a plain layout script so a cut is a one-line change and a rebuild reproduces every other decision exactly. See `references/davinci-resolve.md` (Cut-pass workflow).
8. **Verify audio with the right tools.** Whisper `small` hallucinates repeated lines over music and at file ends. Check the tail with `medium` on an isolated segment, per channel, and reconstruct the expected mix from the stems when a user reports an artifact. See `references/self-check.md`.

## Before you start

1. Confirm what's available: `REPLICATE_API_TOKEN`, and at least one voice option (`ELEVENLABS_API_KEY`, Google TTS credentials, or the local fallback in `references/voices.md` — local works with zero API keys, good for a first dry run).
2. Confirm DaVinci Resolve is installed and running if the deliverable needs assembly (`references/davinci-resolve.md` has the MCP setup). If it's not available, the pipeline still produces correct individual clips + a manifest; assembly can happen later or by hand.
3. **Ask the user for the aspect ratio and target duration before generating anything** — this determines `aspect_ratio` on every generation call and is expensive to fix after the fact (a session this skill was built from generated 3 shots in the wrong aspect ratio because this wasn't locked down first).

## Pipeline

Work through these phases **in order**, and don't skip the verification step at the end of each one. A shot that fails verification gets regenerated *before* moving on, not patched after the fact.

### 1. Break the script into a shot list

Turn the script/concept into a structured shot list — see `references/shotlist-format.md` for the schema (it's also encoded as `scripts/shotlist_schema.json` for validation). Each shot needs: which character(s) are in it, whether it has dialogue (and the exact line), the camera/action description, and target duration. Flag every shot with 2+ characters now — those need more care (phase 3).

Save the shot list as a manifest file in the project directory (e.g. `shotlist.json`) and update it as you go — every phase below reads and writes to this manifest. This is what makes the pipeline resumable: if a step fails or the session ends, re-running picks up from the manifest's recorded state instead of starting over or silently redoing finished work.

### 2. Lock one reference image per character

For each named character, generate and get explicit approval on **one** reference portrait before generating anything else. This takes iteration — budget for it; a real character lock in the session this skill came from took ~10 regenerations to land age, skin tone, and wardrobe correctly, and that's normal, not a failure.

Read `references/character-consistency.md` before doing this — it covers the identity-lock models (`fofr/consistent-character`, `bytedance/flux-pulid`) that solve the "re-prompt from scratch and hope it matches" problem, which is the single biggest source of wasted generations in the session this skill was built from.

**Do not proceed to phase 3 until every character's reference is explicitly approved** (by the user, or by you against a written description if operating unattended — see `references/self-check.md` for what an automated approval check looks like).

### 3. Generate a dedicated reference image per shot

For shots with only one character, the phase-2 portrait IS the reference — use it directly as `start_image`.

For shots with 2+ characters, or any shot whose pose/composition differs meaningfully from the locked portrait, **generate a new reference image specific to that shot** using the locked character identities as input (identity-lock models, or a well-prompted combined scene — see `references/character-consistency.md` for both approaches and when each applies). Never paste/composite two separate portraits together as a shortcut — it produces a visible seam that doesn't read as one photo and gives the video model a bad anchor. Never reuse one shot's reference image for a different shot just because it's "close enough."

### 4. Generate video per shot

Use `references/replicate-video.md` for exact model IDs, parameters, and the specific bugs already found and fixed (duration must be an int, aspect_ratio is silently ignored once a reference image is set so set it explicitly when there isn't one, pass images as open file handles not base64, kling supports a `start_image`+`end_image` pair for better motion control on two-shots).

After each generation, run the automated checks in `references/self-check.md` (`scripts/qa_check.py`) before moving to the next shot: correct aspect ratio, correct duration, no obvious garbled on-screen text, and — for multi-character shots — a quick visual check that both characters are actually present and distinguishable. Catching a wrong-character generation here costs one regeneration; catching it after lipsync and timeline placement costs the whole chain redone.

### 5. Generate voice

Pick a tier from `references/voices.md` (ElevenLabs API, Google, or local/Replicate Chatterbox) per the project's budget/quality needs, and **have the user audition and approve the voices before generating the full script**. Generate every dialogue line now, named consistently with the shot list (e.g. `shot04_elena.mp3`) so phase 6 can find them without guessing.

### 6. Real lipsync — not a text-prompt placeholder

**Read `references/lipsync.md` before this phase, every time.** The single most expensive mistake in the session this skill was built from was generating 11 "dialogue" shots with a prompt like `lips moving as if saying "..."` and discovering afterward that none of it was actually synced to the real audio — Kling and Replicate video models in general do not do lipsync on their own.

Pick one path per `references/lipsync.md`'s decision tree:
- ElevenLabs' native Avatar + Lip Sync workflow (voice+lipsync+video together, preferred when available)
- The Replicate lipsync bridge (`sync/lipsync-2-pro` or similar) merging the phase-4 silent video with the phase-5 audio

**After every lipsync merge, verify the output actually has an embedded audio stream** (`ffprobe -show_streams -select_streams a`) before marking that shot done in the manifest. A silently-failed merge returning a video-only file is a real failure mode, not a hypothetical.

### 7. Assemble in DaVinci Resolve

Follow `references/davinci-resolve.md`. Set the project's resolution/frame rate explicitly to match what was decided before phase 1. Build bins, import the approved assets (not the discarded regeneration attempts — rename or prefix those clearly instead of leaving a media pool full of ambiguous filenames), place clips on the timeline in order, place the matching audio aligned under each clip.

**Verify the actual timeline, don't just trust that the API calls succeeded.** Use `timeline_frame.capture` to look at real frames at a few points across the edit — confirm the right character/content is actually there, confirm the aspect ratio looks right in context, confirm there's no silent gap. A file-overwrite-in-place gotcha in `references/davinci-resolve.md` caused a fully "correct" set of files to render as corrupted inside Resolve in the session this skill was built from — it looked fine from the API's perspective and was wrong on screen.

If the deliverable needs burned-in captions or a repeating title/end-card format, this pipeline's `ffmpeg` typically can't do that cleanly (no `drawtext`/`libass`) and hand-placing text per shot in Resolve is slower and less consistent than it should be for something that's really a template — generate those elements with Remotion instead (`references/remotion.md`), driven straight from the same `shotlist.json` manifest, then bring the rendered overlay/title clips into the Resolve assembly like any other asset.

### 8. Final pass

Before calling it done: play through (or frame-sample across) the whole timeline, confirm every shot has the audio it's supposed to, confirm no shot reverted to a stale/wrong character, confirm aspect ratio is consistent start to finish. Update the manifest to reflect final status. If this is a project meant to be revisited, leave a short handoff note (what's locked/approved, what's still rough) — don't make the next session re-derive what you already know.

## When something goes wrong mid-pipeline

Don't push forward hoping the next step fixes an earlier problem. If a character reference doesn't match the locked portrait, stop and fix the reference before generating video from it. If a lipsync merge has no audio stream, stop and fix the merge before placing it on the timeline. The manifest exists so "stop and fix" doesn't mean "start over" — only the broken step needs to be redone.

If the same specific failure happens 3+ times in a row (e.g. a character's age keeps drifting no matter how the prompt is reworded), that's a signal to change *approach*, not keep retrying the same approach with slightly different wording — switch to an identity-lock model if you haven't already, or bring the user in on the decision rather than silently burning more generations.

## Reference index

- `references/character-consistency.md` — the core lesson: locking identity across generations, when to use identity-lock models vs. prompting, multi-character scenes
- `references/replicate-video.md` — Kling and other video models, exact params, known bugs and fixes
- `references/replicate-image.md` — flux models, image-to-image refinement, identity-lock models in depth
- `references/voices.md` — ElevenLabs / Google / local voice generation tiers
- `references/lipsync.md` — real lipsync paths and the audio-stream verification step
- `references/audio-music.md` — background music/SFX generation
- `references/editing.md` - editing craft: pacing, cuts versus dissolves, continuity at cuts, dialogue audio, final-pass checklist
- `references/davinci-resolve.md` — MCP setup, assembly workflow, concrete gotchas hit in production
- `references/remotion.md` — burned-in captions, title/end cards, and overlays driven straight from the shot-list manifest
- `references/self-check.md` — the automated QA checks run between every phase
- `references/shotlist-format.md` — the manifest schema that drives the whole pipeline
