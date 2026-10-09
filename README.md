# HAVEMINDVIDEO

A Claude Code skill for producing finished, multi-character, lip-synced video ads and shorts — Replicate for image/video generation, ElevenLabs/Google/local for voice, DaVinci Resolve for assembly.

Built after a session that burned real API spend on exactly the mistakes this skill now catches automatically: character identity drifting across generations, "lipsync" that was actually just a text prompt with no real sync to the audio, wrong aspect ratios going unnoticed, and generation failures that looked successful at the API level while being wrong on screen. Every piece of guidance in here traces back to a specific real failure — see `references/` for the details, not just the rules.

## What this is for

Turning a script or a concept into a finished video where:
- The same characters look like the same characters across every shot
- Dialogue is actually synced to the audio, not just prompted to look like it might be
- Mistakes get caught before they propagate into the next phase, not discovered in a finished timeline
- The whole thing can be assembled into a real DaVinci Resolve project, not just a folder of disconnected clips

## What this is not

Not a one-shot "generate a video from a prompt" tool — there is no such thing yet that produces reliable multi-character, dialogue-driven results. This skill assumes iteration (especially on locking character identity) and gives you a process and tooling to make that iteration cheap and trackable instead of repetitive guesswork.

## Requirements

- A [Replicate](https://replicate.com) API token for image/video generation
- At least one voice option: [ElevenLabs](https://elevenlabs.io) API key, Google Cloud/Gemini TTS credentials, or nothing at all (a local, free, MIT-licensed fallback is documented in `references/voices.md`)
- [DaVinci Resolve](https://www.blackmagicdesign.com/products/davinciresolve) (free or Studio) if you want automated timeline assembly, via the [`davinci-resolve-mcp`](https://github.com/samuelgursky/davinci-resolve-mcp) MCP server — optional; the pipeline produces correct individual clips either way
- `ffmpeg` on PATH (verification/QA checks use `ffprobe`)
- Python 3.10+

## Getting started

1. Clone this repo (or add it as a Claude Code skill directory — see `SKILL.md`).
2. Set `REPLICATE_API_TOKEN` and whichever voice credentials you're using.
3. Read `SKILL.md` — it's the entry point and walks through the whole pipeline phase by phase, linking out to the `references/` docs that matter at each step.
4. Start a project: a script/concept, a target aspect ratio and duration, and let the pipeline build out a `shotlist.json` manifest as it goes.

## Structure

```
SKILL.md                         entry point — the pipeline, phase by phase
references/
  character-consistency.md       the core lesson: locking identity across generations
  replicate-video.md             Kling and other video models, exact params, known bugs
  replicate-image.md             flux models, image-to-image, identity-lock models
  voices.md                      ElevenLabs / Google / local voice generation
  lipsync.md                     real lipsync paths + the verification step that matters
  audio-music.md                 background music/SFX generation
  davinci-resolve.md             MCP setup, assembly workflow, production gotchas
  self-check.md                  the QA checklist run between every phase
  shotlist-format.md             the manifest schema that drives the pipeline
scripts/
  shotlist_schema.json           JSON Schema for shotlist.json
  qa_check.py                    automated verification (aspect ratio, duration, audio-stream presence)
  test_qa_check.py               self-test for qa_check.py's logic
```

## Contributing

This is young and built from one team's hard-won lessons — it's very likely incomplete or wrong in places nobody's hit yet. If something in here doesn't match current reality (Replicate model IDs drift constantly, APIs change), or you've found a better pattern for a piece of this pipeline, contributions are welcome. The docs are written to be specific and falsifiable on purpose — if a doc states something that turns out not to be true anymore, that's a bug report, please open an issue or a PR.

## License

MIT — see `LICENSE`.
