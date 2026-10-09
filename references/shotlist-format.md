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
