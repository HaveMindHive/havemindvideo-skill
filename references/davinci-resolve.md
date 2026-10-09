# DaVinci Resolve — Assembly Reference

How HAVEMINDVIDEO SKILL drives DaVinci Resolve to assemble generated clips into a timeline: setup, the operations you'll actually use, and the gotchas that will burn you if you don't read them first.

## Quickstart

1. Install the community MCP server: `npx davinci-resolve-mcp setup`. This is [`samuelgursky/davinci-resolve-mcp`](https://github.com/samuelgursky/davinci-resolve-mcp) — a actively maintained, ~3,400-star project with broad API coverage (300+ methods). Follow its setup prompts to register the MCP with your Claude Code config.
2. Launch DaVinci Resolve (Studio or free — scripting works on both) and open the project you want to work in.
3. Verify the connection before doing anything else:
   ```
   resolve_control(action="runtime_mode")
   ```
   This tells you Resolve is running and reachable without touching project state. If it reports a wedged/no-database state, quit and restart Resolve — don't try to work around it, every subsequent call will silently misbehave.
4. Confirm which project is open:
   ```
   project_manager(action="get_current")
   ```

## Common operations

### Organize the media pool into bins

```
media_pool(action="add_subfolder", params={"name": "Reference Images"})
media_pool(action="add_subfolder", params={"name": "Shot Clips"})
media_pool(action="add_subfolder", params={"name": "VO Audio"})

media_pool(action="set_current_folder", params={"path": "Master/Shot Clips"})
media_pool(action="import_media", params={"paths": ["/abs/path/shot01.mp4", "/abs/path/shot02.mp4"]})
```

`import_media` always imports into whatever folder `set_current_folder` last pointed at — set the folder first.

### Rename clips deliberately

AI generation tools produce cryptic filenames (`epoch_img_raw_a93f...hash....png`). Once an asset is locked/approved, rename it in the pool so the bin stays navigable:

```
media_pool_item(action="set_name", params={"clip_id": "<id>", "name": "REF_CharacterName_FINAL"})
```

For a superseded asset you want to keep around temporarily (in case you need to revert), rename it with a `zz_discard_` prefix instead of deleting it immediately — it sorts to the bottom and stays out of the way without losing the option to go back.

### Set canvas resolution and frame rate explicitly

Don't assume Resolve's default (1920×1080 landscape) — set it before importing anything, e.g. for a vertical social ad:

```
project_settings(action="set_setting", params={"name": "timelineResolutionWidth", "value": "1080"})
project_settings(action="set_setting", params={"name": "timelineResolutionHeight", "value": "1920"})
```

Read current settings the same way with `get_setting`.

### Create a timeline from clips

For an initial rough-cut assembly, `create_timeline_from_clips` appends a list of clips end-to-end into a brand-new timeline in one call:

```
media_pool(action="create_timeline_from_clips", params={
  "name": "Rough Cut",
  "clip_ids": ["<id1>", "<id2>", "<id3>", "..."]
})
```

Clips land in shot order, back to back, no gaps.

### Verify what's actually on the timeline

Don't trust that an API call "succeeded" at the data level — render the actual frame and look at it:

```
timeline_frame(action="capture", params={"frame": 86450, "quality": "frame", "max_width": 600})
```

Returns a real rendered image at that timeline frame. Timeline frame numbers are **absolute**, not relative to the first clip: a project whose timeline starts at timecode `01:00:00:00` at 24fps starts at frame `86400`, not `0`. Convert: `frame = 86400 + (seconds_into_timeline * fps)`.

### Delete clips (two-step confirm)

Deleting from the media pool is deliberately not a single call:

```
media_pool(action="delete_clips", params={"clip_ids": ["<id1>", "<id2>"]})
# → returns {"confirm_token": "...", "preview": {"names": [...], "clips_lost": N}}, expires ~300s

media_pool(action="delete_clips", params={"clip_ids": ["<id1>", "<id2>"], "confirm_token": "<token>"})
# → actually deletes
```

Use the preview in the first response to sanity-check exactly what you're about to lose before confirming.

## Gotchas

**`project_manager(action="create")` creates a whole new PROJECT, not a timeline.** This is the single easiest mistake to make, and it's silent: if you mean "new timeline," you want `media_pool(action="create_timeline")` or `create_timeline_from_clips` — both operate inside the *current* project. `project_manager.create` switches you into a brand-new, empty project under a different name. If you catch yourself having done this, `project_manager(action="load", params={"name": "<original project>"})` to get back, then `project_manager(action="delete", params={"name": "<accidental project>"})` to clean up.

**Overwriting a media file in-place at the same path breaks playback, even though the new file is valid.** If you regenerate a clip and want to swap it in, do not just overwrite the original file and call `media_pool(action="refresh")`. Resolve caches metadata/proxy info tied to the original bytes at that path, and a same-path swap produces "Error decoding full resolution media" errors — confirmed with `ffprobe` showing the replacement file is a perfectly valid h264 file at the right resolution/duration. **Fix:** give the corrected file a new, distinct filename, then force a clean relink:
```
media_pool_item(action="replace_clip", params={"clip_id": "<id>", "path": "/abs/path/shot01_v2.mp4"})
```

**`AddTransition()` on a timeline item does not reliably work via the scripting API** — it returned `None`/no-op in testing. For a simple fade, use `set_fades` on the timeline item instead, and note it takes a **dict**, not positional args:
```
timeline_item(action="set_fades", params={"FadeIn": 24.0, "FadeOut": 24.0})  # frames, not seconds
```
This produces a fade-through-black at the cut, not a true overlapping cross-dissolve. A real blended dissolve still needs to be added by hand in the Resolve UI, or built by generating an actual overlapping transition clip.

**There's no ripple-insert-at-position API.** To insert a clip into the middle of an already-packed track, or close a gap: capture the full ordered clip list (including any items on alternate tracks and their positions), wipe the track(s), then rebuild with a single `AppendToTimeline`-style call — which packs clips back-to-back with no gaps automatically — then re-place every alternate-track item at its new, shifted position. Don't try to hand-roll ripple math against individual clip start/end times; there's no `SetStart`/`SetEnd` on a timeline item to do that with.

**An audio clip's `Duration` property can be unreliable for exact frame-count math.** It can read `''` for the `Frames` property entirely on some imports, and even where `Duration` (format `HH:MM:SS:FF`) is populated, it can disagree with the file's actual length. When precise audio placement/sync matters (e.g. aligning a voiceover line to a specific video clip's start frame), cross-check against the real file:
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 voiceover.mp3
```
and compute frames from that, not from the Resolve-reported `Duration` alone.

**`GrabStill()`/preview captures can desync from the real playhead** after a Resolve crash or a heavy scripted rebuild — `SetCurrentTimecode` can return success while the UI playhead doesn't actually move, so every subsequent still capture returns the same stale frame. If several different-timecode captures all come back identical, don't trust them; sanity-check with a frame deep inside a clip's known content (not right at a cut) before concluding something in the edit is actually broken.

**Compositing an overlay with `ffmpeg` instead of Resolve's own PIP/transform tools:** check the actual source clip's native resolution first (`ffprobe -show_entries stream=width,height`) — AI-generated clips are frequently NOT at the project's canvas resolution (e.g. a 1088×1904 Replicate output inside a 1080×1920 timeline). Position/scale math done in canvas-space must be rescaled by `source_dimension / canvas_dimension` before passing to ffmpeg's `overlay=x:y` filter, or the overlay lands off-screen. Also pass `-r <project_fps>` explicitly — ffmpeg can silently default a composited output to 25fps even when every input is 24fps, which Resolve then retimes/truncates on import, producing a clip that's one frame short in a way that looks like an unexplained gap.

**If you do need `TimelineItem.SetProperty` for a picture-in-picture or overlay:** `ZoomX`/`ZoomY`, `Pan`, `Tilt`, `CompositeMode`, `CompositeEnabled`, and `Opacity` are the keys that work. `Pan`/`Tilt` are pixel offsets from canvas center *at the project's actual timeline resolution* — check `timelineResolutionWidth`/`Height` first, don't assume 1080×1920. Positive `Tilt` moves the image up; positive `Pan` moves it right. `ZoomX`/`ZoomY` are relative to the clip already being scaled to fit the frame, so `0.22` means "22% larger than fit-to-frame," not "22% of canvas pixels."

## When you need more than this

Everything above covers what a simple ad or short-form assembly actually needs: bins, import, rough-cut timeline, basic fades, verification by rendering a frame. The underlying community MCP server exposes far more — color grading, Fusion compositing, multicam sync, render presets, and hundreds of other methods — for when a project outgrows a straightforward cut. Reach for those only when the job calls for them; for HAVEMINDVIDEO SKILL's main use case (assemble generated shots + voiceover into a finished short video), the operations in this doc are the whole workflow.
