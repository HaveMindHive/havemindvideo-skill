# Shot list / manifest format

The manifest (`shotlist.json` in the project directory) is the pipeline's state. Every phase reads it to know what to do next and writes back to it to record what happened — this is what makes the pipeline resumable instead of all-or-nothing.

Schema lives at `scripts/shotlist_schema.json` for validation. Shape:

```json
{
  "project": "example-ad",
  "aspect_ratio": "9:16",
  "fps": 24,
  "characters": {
    "elena": {
      "description": "short text description for initial seed generation",
      "reference_image": "images/REF_elena_final.png",
      "status": "approved"
    }
  },
  "shots": [
    {
      "id": "shot01",
      "characters": ["elena", "jane"],
      "dialogue": null,
      "action": "Wide establishing shot, both characters at a table.",
      "duration_s": 5,
      "reference_image": "images/shot01_reference.png",
      "reference_status": "approved",
      "video_file": "clips/shot01.mp4",
      "video_status": "qa_passed",
      "audio_file": null,
      "lipsync_file": null,
      "lipsync_status": "n/a",
      "timeline_status": "placed"
    },
    {
      "id": "shot02",
      "characters": ["elena"],
      "dialogue": "Close your eyes, dear.",
      "action": "Medium shot, Elena gestures.",
      "duration_s": 5,
      "reference_image": "images/REF_elena_final.png",
      "reference_status": "approved",
      "video_file": "clips/shot02_silent.mp4",
      "video_status": "qa_passed",
      "audio_file": "audio/shot02_elena.mp3",
      "lipsync_file": "clips/shot02_lipsynced.mp4",
      "lipsync_status": "verified",
      "timeline_status": "placed"
    }
  ]
}
```

## Status values

Each `*_status` field tracks where that piece of the shot is, so re-running the pipeline knows what still needs doing instead of redoing everything or silently skipping something unfinished:

- `reference_status`: `pending` → `generated` → `approved` (or `rejected`, regenerate)
- `video_status`: `pending` → `generated` → `qa_passed` (or `qa_failed`, regenerate)
- `lipsync_status`: `n/a` (no dialogue), `pending`, `merged`, `verified` (audio stream confirmed present — see `references/self-check.md`), or `failed`
- `timeline_status`: `pending` → `placed` → `verified` (checked via an actual rendered frame, not just placement)

## Rules the format encodes

- A shot only advances to `video_status: qa_passed` after the checks in `references/self-check.md` actually ran against the file — not automatically on generation.
- A shot with dialogue doesn't count as done until `lipsync_status: verified`, not merely `merged` — merged-but-unverified means the audio-stream check hasn't run yet and the file shouldn't be trusted.
- `reference_image` for a multi-character shot is a dedicated image for *that shot*, never another shot's reference path reused — if you find yourself about to write the same `reference_image` path into two different shots with different `action` text, stop and generate a proper one instead.

## Dialogue pacing: check word count against duration before generating anything

Natural spoken English runs roughly **2.5 words per second**. Before generating voice or video for a dialogue shot, check the line against its `duration_s`:

| `duration_s` | Target word count |
|---|---|
| 5s | 10-12 words |
| 10s | 22-25 words |
| 15s | 33-37 words |

A line that's too long for its shot duration doesn't fail loudly — the voice generation "succeeds," the lipsync merge "succeeds," and the mismatch only becomes obvious when a shot's dialogue audio runs well past its video (forcing an ugly extend/loop) or a short line leaves awkward dead air. Count words before submitting a line for generation, not after a shot already needs rework. If a line is over target, cut it or split it across two shots rather than hoping the sync-mode's loop/trim behavior quietly absorbs the mismatch.

## The manifest is intent, the filesystem is truth

The `shotlist.json` manifest records what the pipeline *believes* has happened. It can drift from what's actually on disk — a generation that failed partway, a file that was manually deleted or replaced outside the pipeline, a status field that never got written back after an interrupted run. **On every resume, reconcile before trusting the manifest**: check that every file path the manifest claims exists actually exists, and that the ones marked `qa_passed`/`verified` still pass those checks (`scripts/qa_check.py` does exactly this). Don't act on a status field without confirming the artifact behind it is real — a manifest claiming a shot is done is a claim to verify, not a fact to build on.

## Leave a human-readable status alongside the JSON

The JSON manifest is for the pipeline; it's not something a person (or a future session) wants to read cold to understand where a project stands. After any significant state change, regenerate a short human-readable summary alongside it — a phase table (how many shots at each status), what's blocked or needs a decision, and what the next action is. This is cheap to produce from the manifest and saves a future session (yours or someone else's) from re-deriving project state by reading raw JSON or re-asking the user what's already been decided.
