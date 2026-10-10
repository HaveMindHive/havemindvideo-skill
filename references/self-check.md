# Self-check: verify before trusting

Every API call that "succeeds" (returns 200, returns a file URL) is not the same as that output being *correct*. This doc is the checklist that catches the gap — run it between every phase of the pipeline, not just at the end.

The underlying discipline: **check the actual artifact, not the API response.** A generation call succeeding tells you the model ran. It tells you nothing about whether the right character showed up, the aspect ratio is right, the audio actually synced, or the clip is even playable. Every check below is a real failure that happened and went undetected until someone looked at the actual output.

## After generating a reference image

- [ ] **Open and look at it.** Don't just confirm the file exists — a generation can "succeed" and still be wrong (wrong age, wrong character entirely, wrong number of people).
- [ ] If it's a multi-character shot: are both/all characters actually present and visually distinguishable from each other? (Confirmed failure mode: a 2-person reference rendered with matching outfits and the model silently dropped one character's distinguishing feature.)
- [ ] Does it match the locked character reference closely enough to use as a video seed? If this is a *new* shot reference (not the original lock), compare side by side — age, skin tone, hair, wardrobe should all still read as "the same person."

## After generating video from an image

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,avg_frame_rate -of default=noprint_wrappers=1 shot.mp4
```

- [ ] **Resolution/aspect ratio matches the project spec.** A text-to-video call with no reference image can silently default to landscape even when every other shot in the project is vertical — this won't show up unless you actually check the file's dimensions, not just that generation succeeded.
- [ ] **Duration is in the expected range.** A video model can silently return a different duration than requested.
- [ ] **Extract 2-3 frames and look at them** (`ffmpeg -vf "select=eq(n\,N)" -vsync 0 -update 1 frame.png`). Check for:
  - Garbled/gibberish on-screen text (a known AI-video artifact — looks like fake watermark text baked into the frame). Add "no on-screen text, no watermark" to the prompt and regenerate if found.
  - The right character(s), still recognizable as the locked identity.
  - For a multi-character shot: both characters still present through the clip, not just at the seed frame.

## After a lipsync merge

```bash
ffprobe -v error -show_streams -select_streams a merged.mp4
```

- [ ] **The output has an embedded audio stream.** This is not optional to check — a failed or empty lipsync merge can return a file URL with no error, and that file can be video-only. Don't place a "lipsynced" clip on a timeline until this has actually been confirmed on the file, not assumed from the job returning successfully.
- [ ] Spot-check that the mouth movement looks plausible against the audio (not frame-accurate verification, just "does this look roughly right," especially for turned/profile faces which are a known glitch case for lipsync models).

## Before moving an asset into the final assembly

- [ ] Is this the *approved* version, or an earlier discarded attempt? A project that iterated through several regeneration attempts per shot can easily have 3-4x as many files as final shots — name/prefix discarded attempts clearly (e.g. `zz_discard_`) the moment they're superseded, don't rely on remembering which timestamp was the good one.
- [ ] Does the filename communicate what it is? Cryptic auto-generated filenames (a hash-suffixed name from a generation tool) should be renamed to something like `shot04_elena_final.mp4` before they end up in a media pool with dozens of other clips — this is cheap to do immediately and expensive to untangle later.

## After placing clips on a timeline

- [ ] **Render and look at actual frames from the timeline itself**, not the source clips — a file-relink issue, a wrong-track placement, or a gap can all produce a timeline that looks correct from the API's perspective (clip metadata, in/out points all report as expected) while actually rendering wrong or corrupted on screen. Capture a frame at the start of each shot's span and look at it.
- [ ] Scan for gaps and overlaps across every track — these accumulate silently across multiple editing passes and won't surface until playback.
- [ ] Confirm aspect ratio and resolution are consistent for the whole timeline, not just the shots checked individually.
- [ ] If driving Resolve via `samuelgursky/davinci-resolve-mcp`, run its own project-health pre-flight before calling assembly done: `project_manager(action="lint")` → `{ok, counts, issues}`. It catches structural problems (mixed frame rates across timelines, an empty timeline, offline media, unset render format) that a frame-by-frame visual check won't surface. See `references/davinci-resolve.md`.

## When to stop and change approach instead of retrying

If the same specific failure recurs 3+ times with only prompt wording changed between attempts (a character's age keeps drifting, a wardrobe keeps bleeding between two characters, a merge keeps failing the same way), that's a signal the *technique* is wrong, not that the next wording tweak will fix it. Switch tools (identity-lock model instead of text re-prompting, a different lipsync model, a dedicated per-shot reference instead of a reused one) rather than spending a fourth, fifth, sixth attempt on the same approach. If unattended and genuinely stuck after a technique change, stop and flag it rather than continuing to spend API budget hoping for a different result from the same method.

## Contact-sheet QA (do this for every generated clip)

Frame 1 hides most failures. For each clip, grab four frames across its length (8%, 40%, 70%, 95%), put them in a row, and stack the clips you are reviewing into one image. Then look for:

- identity drift (hair color/brightness, age, face shape changing mid-clip),
- prop morphing (an object turning into another object), props held backwards,
- hands: extra, fused or ghosted fingers, especially during hand-offs,
- set changes (tablecloth, wall, furniture) versus the established scene,
- on dialogue shots, that the right person is the one speaking.

Cheap to do (ffmpeg + PIL), and it catches the problems before they are placed on a timeline.

## Spend discipline
Generate in small batches, look at the result, then scale. Do not launch a full-script batch before one pilot shot of each *type* (solo dialogue, two-shot, prop action) has passed review.

## Render QA checklist
1. Duration matches the EDL total (frames / fps).
2. `blackdetect` shows only the intended fades and dips.
3. `volumedetect` per section: dialogue about -18 to -20 dB mean, music under speech well below it.
4. A frame sheet across any section that was edited late, to confirm the right picture holds long enough to read (screens and inserts should stay up long enough for a viewer to read them).
5. Check every clip's frame rate before it goes on the timeline.
