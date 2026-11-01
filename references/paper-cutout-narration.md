# Narration-only illustrated shorts (paper cut-out, no lipsync)

Workflow learned building a ~100 second vertical explainer (10-21-2026) with paper cut-out stick figures, Replicate stills and clips, a generated narration, and a DaVinci Resolve assembly. Use it when the characters do not talk: a voiceover runs over illustrated shots. There is no lipsync step, so phases 5 and 6 of the main pipeline collapse into "generate and verify the narration".

Credit: the direction (style, "no time target", "text goes on afterward", "do not clone a real person's voice") came from tUrUq. The skill records it; he taught it.

## 1. Order of work (cheap decisions first)

1. Script into numbered shots, one narration line or two per shot. Save a manifest (`shotlist.json`) with the narration text per shot.
2. Style lock: generate 3 candidate stills of the characters in the target style (`google/nano-banana`, about $0.04 each, `aspect_ratio` 9:16). Let the user pick one. Save it as `REF_style_lock_FINAL`.
3. One reference still per shot with the style lock passed as `image_input`. Look at every still before animating.
4. Pilot one shot of each type (two figures, solo figure, props only) through Kling before batching the rest.
5. Narration (section 4), then layout script, overlays, sound bed, Resolve assembly, render, verify.
6. Keep every stage scripted from the manifest so a change is one edit and a rebuild.

## 2. Text: never let the video model write it

Image and video models invent text: numerals on rulers and clock faces, printed labels on boxes, "Colored Paper Blocks" on a cardboard box, gibberish on a dial. Rules that worked:

- Put "no numerals, no letters, no writing anywhere; clocks, rulers and dials show tick marks only" in every still prompt, and name the specific hazard (clock, ruler, box, sign).
- Look at every still and every contact sheet frame for stray text before moving on. Regenerate the still, not the clip.
- All real words (titles, labels, captions) are overlays made afterward. Draw them with Pillow as paper letters (ransom-note tiles for short words, cardstock tags for long ones, cream strips for captions), composite to a transparent ProRes 4444 `.mov` (see `scripts/paper-cutout/layout.py`), and place it on a video track in Resolve. ffmpeg here has no `drawtext`.

## 3. Picture generation lessons

- A reference that contains a thread, string or cable gets that line animated into a long black wire. If two takes do it, change the reference (remove the element), do not retry the prompt.
- Put "two dot eyes, no mouth" and "no smile, mouth, nose, eyebrows" in the negative prompt. Kling adds smiles when figures "look at each other".
- Ask for the motion you want, and say what must not move ("the clocks stay fixed, only the hands turn"). Otherwise a prop drifts out of frame.
- The style lock leaks props (a sun appeared in unrelated stills). Add "no sun and no extra props unless the scene says so".
- A narration line longer than the clip needs a longer clip, not a frozen last frame. Kling clips are 5 or 10 seconds; give long lines a 10 second clip. A hold of more than about half a second reads as dead air.
- Stop-motion feel is a post step: `fps=12` then `fps=24` duplicates frames. Do it in the conform step, not in the prompt.
- Gentle push-in or pull-out per shot (alternate) with `zoompan` after the 12 fps step adds life cheaply.

## 4. Narration

See `references/voices.md` for the voice options. Process that worked:

1. Generate each shot's line separately, then trim leading and trailing silence and loudness-normalize each file (`silenceremove`, `loudnorm=I=-18`, mono 48 kHz).
2. Transcribe every take with Whisper `medium` and compare to the script. A coined word ("spacetime") or a letter ("c" heard as "sea") is a false alarm; a dropped or changed word ("coexisting" heard as "coexist in") is real. Retry up to four takes per line and keep the first clean one (`scripts/paper-cutout/gen_vo.py`).
3. Keep Whisper word timestamps per line. They drive caption timing and phrase breaks.
4. Do not impose a runtime. Let the narration set the length and make the picture cover it (longer clips, slower clips up to about 1.3x). Only trim if the user asks for a length.
5. If the user asks for a voice that sounds like a real named person, do not clone or imitate that person. Pick a stock voice in the same register (age, accent, pace) and say so.

## 5. Captions

- Break at phrases, not at an even word count. Chunk by sentence, then a small dynamic program over 2 to 7 word chunks that avoids ending on a function word ("as", "by", "the") and prefers comma breaks. Time each chunk from the word timestamps (character interpolation handles Whisper splitting a coined word in two).
- Keep captions in the empty lower area of the frame, above the platform's UI. Move lettering that covers a figure.

## 6. Transitions and sound

- Hard cut where the narration continues a thought. Short dissolves (8 frames) at soft beat changes. A torn-paper wipe (`scripts/paper-cutout/fx.py`) hides the cut at the biggest beat changes; the cut lands under the paper at wipe frame 8.
- Dissolves: alternate V1/V2 and fade the upper item (see `davinci-resolve.md`). Wipes: a ProRes 4444 clip on its own top track, centered on the cut. The wipe covers captions as it passes, which looks right.
- Sound: bake one bed (music ducked about 8 dB under narration with 120 ms ramps, paper whooshes at wipes, soft thumps when lettering lands) with `scripts/paper-cutout/bed.py`; Resolve cannot set levels through the API. MusicGen on Replicate needs a pinned version id (`replicate.run("meta/musicgen:<version>")`); the bare model name returned 404.

## 7. Final checks (do all of them)

1. `render.verify_output` with `expected_frames`.
2. `ffprobe` that the file has a video and an audio stream; `blackdetect`; `ebur128` (this build landed at about -15 LUFS with music).
3. Transcribe the RENDERED file with Whisper and diff it against the script. This caught a render that still carried the old narration after the lines had been rewritten (see the same-path audio gotcha in `davinci-resolve.md`).
4. Contact sheet of frames across the render, looking for stray text, wrong captions, and holds.
5. Say plainly what changed and what did not, and keep earlier versions as fallbacks.

## 8. Scope discipline from this project

- When the user says "stick with what we have", stop adding scenes. In this build three extra scenes were generated and thrown away because the user then restricted the change to new narration plus at most one or two shots. Ask or confirm scope before generating new visuals for a script rework.
- Do not put a personal story or a named third party's situation in public copy without the user's explicit yes.
- When the user states a stance the script must carry (here: neither camp is placed above the other, and the physical account is not "what real is"), re-read every line for implied ranking, word order included.
