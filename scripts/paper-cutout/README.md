# paper-cutout helper scripts

Generic helpers extracted from a narration-only illustrated short (see `../../references/paper-cutout-narration.md`). They expect a project folder with `shotlist.json` (shots with `id`, `narration`, `audio_file`, `characters`, `action`), a `clips/` folder of Kling outputs named `{id}_v{N}.mp4`, and an `audio/` folder.

- `gen_vo.py [voice] [speed]` ElevenLabs v3 preset voice via Replicate, one file per shot, Whisper-verified with retries, trimmed and loudness-normalized, word timestamps saved.
- `layout.py` frame-exact timeline from the audio lengths: conforms clips (cover-crop to 1080x1920, stop-motion cadence, push-in, slow-down up to 1.3x), builds a transparent overlay `.mov` (paper letters, tags, phrase-aware captions timed from word timestamps) and writes `edl.json` for the Resolve build. Fill `LABELS` for your own on-screen words.
- `fx.py` torn-paper wipe transition as a ProRes 4444 `.mov` (cut lands on frame 8 of 16).
- `bed.py` bakes one sound bed from `edl.json`: music (supply `audio/music_bed_raw_v1.wav`) ducked under the narration, whooshes at wipes, thumps at lettering.

Rules: new filenames whenever content changes (Resolve serves stale media for a regenerated file at the same path), and always transcribe the rendered file against the script.
