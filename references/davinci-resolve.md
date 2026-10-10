# DaVinci Resolve — Assembly Reference

How HAVEMINDVIDEO SKILL drives DaVinci Resolve to assemble generated clips into a timeline: setup, how to work with this server reliably, the operations you'll actually use, and the gotchas that will burn you if you don't read them first.

This doc covers the **compound server** (the default mode — one tool per domain, an `action` string picks the operation; keeps context lean). A granular full-surface mode exists (one tool per API method, 300+ tools) for power users; you won't need it for the workflow this skill covers.

## Quickstart

1. Install the community MCP server: `npx davinci-resolve-mcp setup`. This is [`samuelgursky/davinci-resolve-mcp`](https://github.com/samuelgursky/davinci-resolve-mcp) — an actively maintained, ~3,400-star project with broad API coverage. Follow its setup prompts to register the MCP with your Claude Code config.
2. Launch DaVinci Resolve (Studio or free — scripting works on both) and open the project you want to work in.
3. Verify the connection before doing anything else:
   ```
   resolve_control(action="launch")        # safe to call even if Resolve is already running
   resolve_control(action="runtime_mode")
   ```
   `runtime_mode` tells you Resolve is running and reachable without touching project state — see the **Headless and "wedged" state** gotcha below before you trust a quiet success.
4. Confirm which project is open:
   ```
   project_manager(action="get_current")
   ```

## Working with this server reliably

### Read the `_operation` envelope, not just the top-level result

Every compound-tool call returns an `_operation` block alongside its normal payload:

```json
{
  "success": true,
  "...": "...",
  "_operation": {
    "status": "success",
    "verification": { "status": "unverified", "checks": [], "contradiction": false },
    "changes": { "items_added": 3 }
  }
}
```

Three things to actually read, not skim past:

- **`verification.status`** — `"unverified"` means *no evidence was reported*, not "checked and found clean." `"contradiction"` means Resolve itself reported success and a readback disagrees — **stop on that one**, something is actually wrong, don't keep building on top of it.
- **`changes`** — present only when the action reported one. Its *absence* means "not reported," never "nothing changed." Don't read a missing `changes` block as a no-op.
- **`status`** can be `success | partial | blocked | failed`. `blocked` means a confirm-gate is waiting (see the two-step delete pattern below) — the payload still carries a `confirm_token` and `preview` to act on.

### One read beats five: `project_manager.snapshot`

Instead of chaining `get_current` + `timeline.get_current` + `probe_timeline_structure` + `detect_gaps_overlaps` separately, one call gives you all of it:

```
project_manager(action="snapshot", params={"include": ["timeline"], "track_types": ["video"]})
```

`include` picks which sections you get (`project`, `timeline`, `gaps_overlaps`, `render`, `media_pool`); `item_limit` (default 200) caps how many timeline items come back. This is the right default state-check before planning any edit, not a chain of separate calls.

### Pre-flight health check: `project_manager.lint`

Before calling an assembly "done," run the project's own health check rather than eyeballing it:

```
project_manager(action="lint")
# → {ok, counts, issues}
```

Flags: mixed frame rates across timelines, an empty timeline, unset render format, offline media, and a few other structural problems — composed from existing read-only probes, safe to call any time.

### Report a real server bug instead of working around it silently

If a tool call looks like it's hitting an actual defect in the MCP server (not a mistake in your own call), don't quietly route around it and lose the information:

```
resolve_control(action="report_issue", params={"kind": "bug", "title": "...", "summary": "..."})
```

Drafts a GitHub issue with the failing action/error, expected vs. actual, and redacts paths/usernames/secrets — it **files nothing itself**, it hands you a URL to review and submit.

## Common operations

### Organize the media pool into bins

```
media_pool(action="add_subfolder", params={"name": "Reference Images"})
media_pool(action="add_subfolder", params={"name": "Shot Clips"})
media_pool(action="add_subfolder", params={"name": "VO Audio"})

media_pool(action="set_current_folder", params={"path": "Master/Shot Clips"})
media_pool(action="import_media", params={"paths": ["/abs/path/shot01.mp4", "/abs/path/shot02.mp4"]})
```

`import_media` always imports into whatever folder `set_current_folder` last pointed at — there's no destination parameter, set the folder first.

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

Clips land in shot order, back to back, no gaps. For precise placement on a specific track/frame instead, use the **positioned** form of `append_to_timeline`:

```
media_pool(action="append_to_timeline", params={"clip_infos": [
  {"clip_id": "<id>", "start_frame": 0, "end_frame": 120, "record_frame": 1200, "track_index": 2}
]})
```

`start_frame`/`end_frame` here are **source** frames (positions within that clip's own media), while `record_frame` is a timeline frame **relative to the timeline start** (frame 0 = the first frame, even when the timeline starts at 01:00:00:00). This is true for BOTH `create_timeline_from_clips` and `append_to_timeline` with `clip_infos`. Passing absolute frames (86400 + n) pushes the item roughly 86400 frames past the end and the readback shows a huge timeline-duration drift: if you see that warning, delete the items and re-place them with relative frames. When Resolve answers append with `None`/`False`/an empty list, that's a real failure (`APPEND_TO_TIMELINE_FAILED`), not success with zero items, check `error.retryable`; it's only true when a readback confirms nothing actually landed, otherwise inspect the timeline before retrying or you risk double-appending.

### Verify what's actually on the timeline — the right tool, not the tempting one

Don't trust that an API call "succeeded" at the data level, and don't trust a clip thumbnail either:

```
timeline_frame(action="capture", params={"frame": 86450, "quality": "frame", "max_width": 600})
```

This renders and returns the **actual frame at that specific timeline position** — the only thing that's frame-accurate. **A media-pool clip thumbnail is not** — it returns the same image for every frame of a given clip (verified: seeking within one clip's range returns byte-identical thumbnail data, changing only at a clip boundary). If you're checking "does this specific moment look right," `timeline_frame.capture` is the only tool that actually answers that; a thumbnail can look fine while the actual frame at your target timecode does not.

Timeline frame numbers are **absolute**, not relative to the first clip: a project whose timeline starts at timecode `01:00:00:00` at 24fps starts at frame `86400`, not `0`. Convert: `frame = 86400 + (seconds_into_timeline * fps)`.

### Delete clips (two-step confirm)

Deleting from the media pool is deliberately not a single call:

```
media_pool(action="delete_clips", params={"clip_ids": ["<id1>", "<id2>"]})
# → returns {"confirm_token": "...", "preview": {"names": [...], "clips_lost": N}}, expires ~300s

media_pool(action="delete_clips", params={"clip_ids": ["<id1>", "<id2>"], "confirm_token": "<token>"})
# → actually deletes
```

Use the preview in the first response to sanity-check exactly what you're about to lose before confirming. `move_clips`/`move_folders` work the same all-or-nothing way as every other `clip_ids`/`folder_ids` batch action below.

### Indexing: easy to get backwards

**`track_index` is 1-based. `item_index` is 0-based.** The first video track is `track_index: 1`; the first clip on it is `item_index: 0`. Mixing these up is a common source of silent off-by-one errors against the wrong clip.

### Placing audio: what you can and can't control via the API

You can place a voiceover/dialogue clip on an audio track with `append_to_timeline`/positioned placement exactly like a video clip. What you generally **cannot** do through this API: adjust a timeline item's Volume, Pan, or EQ — `timeline_item(action="set_audio", params={"Volume": ...})` reports success but Resolve ignores the write (a documented known limitation). The one audio property that does take effect is `AudioSyncOffset`. Practical implication: if your voiceover is too loud/quiet relative to a music bed, normalize it **before** import (at generation/export time) rather than planning to fix levels via the API afterward — final level/pan mixing for this pipeline is a manual Resolve step, not a scriptable one.

### Export the final video

Render-queue workflow, same shape as adding any Resolve render job:

```
render(action="get_formats")
render(action="set_format_and_codec", params={"format": "QuickTime", "codec": "H.265 Master"})
render(action="add_job", params={"TargetDir": "/abs/path/out", "CustomName": "final_cut", "SelectAllFrames": true})
render(action="start")
render(action="is_rendering")
```

For a social-platform deliverable, check whether your server version has **named delivery targets** first — it saves hand-picking format/codec/resolution:

```
render(action="list_delivery_targets", params={"check_availability": true})
render(action="prepare_delivery_job", params={"target": "tiktok", "target_dir": "/abs/path/out"})
```

Named targets like `tiktok`, `youtube`, or `h264_1080p_web` resolve to both the correct Resolve render settings and a QC spec for the output — and fail with the actual available list if your install/license can't deliver that target, rather than silently rendering something else. If your server version doesn't have this, fall back to the manual `render.add_job` flow above with settings matching your platform's spec by hand.

## Gotchas

**A new timeline has one video track.** Asking for `track_index: 2` on a timeline that has only V1 silently places nothing. Call `timeline(action="add_track", params={"track_type": "video"})` first, then append the overlay/cutaway clips to track 2. Pass `"media_type": 1` on cutaways so they do not drag a duplicate audio item along.

**`snapshot` gap detector reports 1-frame gaps between every clip.** The item `end` it returns is the last frame (inclusive), the detector treats it as exclusive, so back-to-back clips look like they have a 1-frame gap. If the next item starts at `end + 1` the cut is clean. Verify with one `timeline_frame.capture` on each side of a boundary if in doubt.

**`timeline_frame.capture` has side effects.** It renders a frame by changing the project's render format/codec to JPEG and moving the playhead, and it may not restore them. After a round of captures, reset the playhead (`timeline_markers.set_current_timecode`) and re-set the render format before queuing a real render, or the deliverable renders in the wrong codec.

**Headless and "wedged" state.** `resolve_control(action="runtime_mode")` returns `{running, headless, instances, database_attached, guidance}`. **`database_attached: false` means the instance is wedged** — it answers version/page/product queries normally (so an ordinary liveness check looks fine), but `CreateProject`/`LoadProject` return `False` forever and some calls never return at all. It does not recover on its own; quit and relaunch Resolve, don't retry. Separately: **never call `SaveProject()` without first checking the project isn't the default, never-saved `"Untitled Project"`** — on a headless instance this specific case blocks forever (Resolve wants to raise a Save-As dialog that can never be answered). Check the project name first; if it's still `"Untitled Project"`, there's nothing to save yet.

**`project_manager(action="create")` creates a whole new PROJECT, not a timeline.** This is the single easiest mistake to make, and it's silent: if you mean "new timeline," you want `media_pool(action="create_timeline")` or `create_timeline_from_clips` — both operate inside the *current* project. `project_manager.create` switches you into a brand-new, empty project under a different name. If you catch yourself having done this, `project_manager(action="load", params={"name": "<original project>"})` to get back, then `project_manager(action="delete", params={"name": "<accidental project>"})` to clean up.

**Overwriting a media file in-place at the same path breaks playback, even though the new file is valid.** If you regenerate a clip and want to swap it in, do not just overwrite the original file and call `media_pool(action="refresh")`. Resolve caches metadata/proxy info tied to the original bytes at that path, and a same-path swap produces "Error decoding full resolution media" errors — confirmed with `ffprobe` showing the replacement file is a perfectly valid h264 file at the right resolution/duration. **Fix:** give the corrected file a new, distinct filename, then force a clean relink:
```
media_pool_item(action="replace_clip", params={"clip_id": "<id>", "path": "/abs/path/shot01_v2.mp4"})
```

**Page context matters — a wrong-page call often returns a plain `False`/error with no hint why.** Several operations only work on a specific Resolve page:

| Operation | Required page |
|---|---|
| Color grading, node graphs, CDL | Color |
| LUT export | Color |
| Gallery stills export / `grab_and_export` | Color, with Gallery panel open |
| Fusion compositions | Fusion |
| Timeline editing, track operations | Edit or Cut |
| Fairlight-specific audio operations | Fairlight |
| Render / deliver | Deliver |
| Media import, storage browsing | Media |

Switch first: `resolve_control(action="open_page", params={"page": "color"})`. For this skill's actual workflow (importing, building a timeline, placing clips) you generally stay on Edit/Media and never need this — but if you hit an unexplained `False`, check the page before assuming something else is broken.

**Batch actions are all-or-nothing.** `delete_clips`, `move_clips`, `move_folders`, `create_timeline_from_clips`, `append_to_timeline`, and similar batch calls fail the *entire* call if even one id in the batch doesn't resolve (`CLIP_NOT_FOUND`/`FOLDER_NOT_FOUND`, with resolved/unresolved ids listed in the error) — nothing is partially applied. Drop stale ids and retry the whole batch; don't assume a partial success happened.

**Renaming the currently-active timeline fails.** `timeline(action="set_name")` returns `False` if you try to rename the timeline you're currently on — switch to a different timeline first, rename, then switch back.

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

Everything above covers what a simple ad or short-form assembly actually needs: bins, import, rough-cut timeline, basic fades, audio placement, export, and verification by rendering real frames. The underlying community MCP server exposes far more — professional color grading and shot-matching, Fusion compositing, multicam sync, a full editorial-intelligence layer (transcript-driven tighten/silence-ripple passes, take ranking, rule-of-six pacing audits, turnover manifests), and hundreds of other methods — built for feature-length conform and finishing work. Reach for those only when a project actually outgrows a straightforward cut. For HAVEMINDVIDEO SKILL's main use case (assemble generated shots + voiceover into a finished short video), the operations in this doc are the whole workflow.
