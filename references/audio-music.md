# Audio & Music — Background Score and SFX

For dialogue/voice generation, see `voices.md`. For syncing dialogue to video, see `lipsync.md`. This doc covers background music beds and sound effects.

## Options

### `meta/musicgen` (Replicate) — default choice, already proven

```python
import replicate

model = replicate.models.get("meta/musicgen")
version_id = model.latest_version.id  # unpinned by name — always fetch current

output = replicate.run(
    f"meta/musicgen:{version_id}",
    input={
        "prompt": "warm acoustic guitar, gentle and hopeful, no drums",
        "duration": 15,
        "model_version": "stereo-melody-large",
    },
)
```

Good general-purpose instrumental generator, free-form text prompt. Like all Replicate models, the version hash drifts — don't hardcode an old one, fetch `latest_version.id` at call time.

### Stable Audio 2.5 (Replicate) — strong alternative for instrumentals/SFX

Worth trying when MusicGen's output feels too "generic AI music" for a given spot, or for short standalone sound effects (a door creak, a whoosh, ambient room tone) rather than a full musical bed. Check `replicate.models.get("stability-ai/stable-audio-...")` for the current exact model slug — Stability's Replicate listings get renamed across versions.

### ElevenLabs Music — if already on ElevenLabs for voice

If the project is already paying for ElevenLabs (see `voices.md`), their Music product reuses the same account/billing instead of adding a second vendor. Convenient when you want one invoice and one API key to manage, at the cost of being locked into their catalog/style.

### Google Lyria (via Gemini API) — pairs with the Google voice fallback

If you're already using Google's TTS as a voice fallback (see `voices.md`), Lyria generation through the same Gemini API account keeps the whole audio stack on one vendor. Like the Google TTS section in `voices.md`, **this hasn't been exercised in this project yet** — verify the current model name and request shape against Google's live docs before relying on it.

## Practical mixing guide (not audio theory — just what actually works in an edit)

- **Duck music under dialogue.** A music bed that's comfortable on its own is almost always too loud once VO starts — pull it down 8-12dB under any line of dialogue, bring it back up in the gaps. If your edit tool doesn't have automatic ducking, do it by hand per VO clip; don't skip it, a music bed that fights the dialogue reads as amateur immediately.
- **Keep SFX short and punchy, not a full musical phrase.** A doorbell, a phone buzz, a page turn — generate or trim to just the hit, don't let a generated SFX clip ramble into ambient texture unless that's specifically what you asked for.
- **Pick a loop point before generating a long bed**, rather than generating one long track and hoping it loops cleanly — either generate a length that exactly matches your target runtime, or generate a short musical phrase explicitly designed to loop and repeat it in the edit. A music model's own natural "ending" rarely loops back into its own beginning cleanly.
- **Generate the bed after the dialogue edit is roughly locked, not before.** Scoring to a moving target wastes generations — get picture-and-dialogue timing settled first, then score to the actual runtime.

## Music arc and sound effects on Replicate (verified)

- **Music:** `google/lyria-2` (`prompt`, `negative_prompt`, `seed`) returns about 32 s of music per call. Make one clip per story section (for example mystical, playful reveal, warm resolution) and crossfade them (about 2.5 s) to follow the story; loop a clip with `acrossfade` against itself if a section is longer than 32 s. State "no drums, no vocals, quiet" in the prompt.
- **Sound effects:** `sepal/audiogen` (`prompt`, `duration`, `classifier_free_guidance`) works but must be called with an explicit version id (`replicate.models.get(...).latest_version.id`, then `model:version`); calling it by bare name returned 404. Useful short prompts: soft fingertip taps on a phone touchscreen, soft magical shimmer swoosh, a single glass chime, velvet fabric rustle, quiet candle crackle (loop as room tone).
- **Duck the music with a curve, not a compressor.** A sidechain compressor either ducked too deep or too little. Computing a 10 ms RMS envelope of the dialogue stem, smoothing it, and mapping it to a music gain between 1.0 and about 0.28 gave a predictable result.
