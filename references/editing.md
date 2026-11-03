# Editing craft

**Credit: these rules come from tUrUq's direction and corrections during the dorm-room ad (10-12-2026): the do-only-what-I-say rule, script over runtime, hard cuts in dialogue and dissolves at scene changes, reaction beats to break up long speeches, eyelines off the lens, continuity of room and wardrobe, one voice over the music at the end, and the cut-first, audio-and-transitions-second order of work. The skill records them; he taught them.**

How to cut a dialogue-driven ad so it flows. **Everything below is a general guideline, not a law.** Exceptions are normal and are often the point (see "Effect: steer the feeling"). The one exception to "exceptions are fine" is the working agreement with the user in the next section: when they name a precise edit, do only that edit. Learned finishing the CelestiaOracle dorm-room ad (10-12-2026). The Resolve mechanics live in `davinci-resolve.md`; this file is about decisions.

## Working agreement with the user (a process rule, not craft)
- **Do only the precise edit asked.** "Cut that clip" means cut that clip, then render. Audio and transitions are a separate, named pass. Never add fades, trims, or mix changes on your own.
- **Follow the user's script, not the runtime estimate.** Run time in a script is a guess. Check the final transcript against the script line by line and list every difference, including agreed additions.
- **Version every render** (`_v4.2_`, `_v4.3_`) and rebuild into a new timeline so any earlier cut can come back.
- **Preview in QuickTime** before placing a new clip. Say plainly what changed and what did not.

## Structure and pacing (guidelines)
- Cut on the line, not on the silence around it. Trim leading and trailing dead air so replies land fast. A scene that sets up (waking, whispering) should be about half the length first drafts suggest.
- Break up a long run of one character's lines with a short reaction shot of the listener. This hides cuts and keeps the other character alive.
- Hold a tarot, phone, or reveal beat just long enough to read. Use silent "doing the thing together" shots as breathing room, with the music brought up.
- A reaction clip can be a different slice of a clip already used (a later in-point), if it is silent and the framing is right.

## Cuts versus transitions (guidelines)
- **Hard cut** inside a dialogue exchange (line, reply, line). Dissolving mid-conversation feels mushy.
- **Dissolve (6 to 10 frames)** at scene or time changes, and into or out of silent inserts and cutaways. Use a longer dissolve into the end card.
- A dissolve needs the outgoing clip to have extra tail frames. Make the picture N frames longer than its audio and cut the audio at the base length so a voice never bleeds into the next scene.
- Do not stack dissolves back to back. If a cut is removed, check the neighbors: the dissolve that used to be there may now join two clips that do not want one.

## Continuity checks at every cut (guidelines)
- Same room, same table, same props, same hands and nails, same wardrobe, same camera side (do not flip 180 degrees between shots).
- Eyelines: a speaker looks at the listener, not the lens, unless the user asked for a look to camera. Check by cropping faces from frames.
- Who is in frame must match the previous shot. Do not place a character where the last shot showed an empty space.
- Phones must read as phones. No stray hands. No palm-up shrugs or other generic AI gestures.
- Colour and brightness: grade the first shots of a hook to match each other (ffmpeg graded copies), not by eye in the viewer.

## Dialogue audio (guidelines)
- Bake loudness before import (about -19 LUFS for mono clips, stereo assets a few dB hotter) so the dialogue spread stays within about 2 LU. Whispers stay quiet on purpose.
- One continuous music bed, not stitched takes. Duck it by layout: low under dialogue, up in silent shots, a bit lower under the voice-over, a clean fade at the end. No fake room tone.
- The ending is one voice over music. No overlapping voices, no leftover tails from the last scene.
- Check the first word of every line. Starting a clip mid-word is the commonest bug, so start line clips at source frame 0 unless the lead-in is silence.

## Sound-design restraint
- Minimal sound effects. A bed that swells or pops under quiet intros distracts from the whispers.
- Normalize a music track's own loudness drift (slow AGC) before ducking it.

## Effect: steer the feeling
"Effect" here does not mean a layover or a filter. It means a choice that changes the mood and directs where the viewer's emotion goes next. Editing is the art of breaking up what the viewer expects, at the right moment. If the cut only follows the pattern, the emotion the audience ends up with is boredom.

- Treat every guideline in this file as a default to be broken on purpose. A hard cut where a dissolve is expected, a held beat longer than comfortable, a dissolve inside a conversation, an unmotivated reaction shot, silence where music was: each can lift, tighten, or turn a scene.
- Before keeping or breaking a guideline, ask what the viewer should feel at that moment (curiosity, warmth, surprise, tension, relief) and what the cut does to that feeling.
- A pattern repeated too evenly goes flat. Vary shot lengths, vary where the cuts land relative to the lines, and let one beat surprise.
- Judge by feel, not by the checklist. The final pass checks for mistakes, not for life. Ask whether any stretch would bore someone watching on a phone, and fix that first.
- Exceptions are made by the editor's intent, so when you break a guideline, be able to say what feeling it serves. If you cannot, follow the guideline.

## Final pass checklist
1. Transcribe the render (Whisper `medium`, tail segments isolated) and compare to the script.
2. Black-frame scan, frame count, duration, loudness per scene.
3. A contact sheet (one frame every 2 seconds) to scan continuity.
4. Open the file in QuickTime. Report every open issue plainly, even small ones.

## Before showing ANY full cut (measured, not eyeballed) — added 11-02-2026
Stop Swiping v4.0 went out at 1:54 with 5-12 s of digital silence inside shots (06, 06b, 11, 12,
15) and no sound bed at all; a 2× / trimmed pass took it to 1:32 with every line intact.
1. Dead air: `ffmpeg -i cut.mp4 -af silencedetect=noise=-38dB:d=0.5 -f null -` and map each gap to
   its shot (edit.json frame counts). In a dialogue shot keep <=0.35 s after the line (more only
   for a deliberate beat Vivi asked for). Silent b-roll/screen recordings: cut to what the viewer
   needs or speed up 1.5-2×.
2. Never digital silence: one continuous music bed (or diner room tone) under the whole ad, ducked
   under dialogue. `assemble.py --music <file>`. If none is chosen yet, ask once, offering 2-3
   options to audition in QuickTime.
3. Runtime vs the brief: state planned vs actual length; if it is >25% over, propose cuts.
4. Every line heard (assembler transcript), first word of each line intact, ends clean.
5. A small contact sheet (<=1024 px wide) checked for continuity jumps between shots.
Do these, fix, THEN show. Report the numbers in one line ("1:32, no gap over 0.4 s, music -18 LUFS").
