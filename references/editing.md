# Editing craft

How to cut a dialogue-driven ad so it flows. Learned finishing the CelestiaOracle dorm-room ad (10-12-2026). The Resolve mechanics live in `davinci-resolve.md`; this file is about decisions.

## Working rules with the user
- **Do only the precise edit asked.** "Cut that clip" means cut that clip, then render. Audio and transitions are a separate, named pass. Never add fades, trims, or mix changes on your own.
- **Follow the user's script, not the runtime estimate.** Run time in a script is a guess. Check the final transcript against the script line by line and list every difference, including agreed additions.
- **Version every render** (`_v4.2_`, `_v4.3_`) and rebuild into a new timeline so any earlier cut can come back.
- **Preview in QuickTime** before placing a new clip. Say plainly what changed and what did not.

## Structure and pacing
- Cut on the line, not on the silence around it. Trim leading and trailing dead air so replies land fast. A scene that sets up (waking, whispering) should be about half the length first drafts suggest.
- Break up a long run of one character's lines with a short reaction shot of the listener. This hides cuts and keeps the other character alive.
- Hold a tarot, phone, or reveal beat just long enough to read. Use silent "doing the thing together" shots as breathing room, with the music brought up.
- A reaction clip can be a different slice of a clip already used (a later in-point), if it is silent and the framing is right.

## Cuts versus transitions
- **Hard cut** inside a dialogue exchange (line, reply, line). Dissolving mid-conversation feels mushy.
- **Dissolve (6 to 10 frames)** at scene or time changes, and into or out of silent inserts and cutaways. Use a longer dissolve into the end card.
- A dissolve needs the outgoing clip to have extra tail frames. Make the picture N frames longer than its audio and cut the audio at the base length so a voice never bleeds into the next scene.
- Do not stack dissolves back to back. If a cut is removed, check the neighbors: the dissolve that used to be there may now join two clips that do not want one.

## Continuity checks at every cut
- Same room, same table, same props, same hands and nails, same wardrobe, same camera side (do not flip 180 degrees between shots).
- Eyelines: a speaker looks at the listener, not the lens, unless the user asked for a look to camera. Check by cropping faces from frames.
- Who is in frame must match the previous shot. Do not place a character where the last shot showed an empty space.
- Phones must read as phones. No stray hands. No palm-up shrugs or other generic AI gestures.
- Colour and brightness: grade the first shots of a hook to match each other (ffmpeg graded copies), not by eye in the viewer.

## Dialogue audio
- Bake loudness before import (about -19 LUFS for mono clips, stereo assets a few dB hotter) so the dialogue spread stays within about 2 LU. Whispers stay quiet on purpose.
- One continuous music bed, not stitched takes. Duck it by layout: low under dialogue, up in silent shots, a bit lower under the voice-over, a clean fade at the end. No fake room tone.
- The ending is one voice over music. No overlapping voices, no leftover tails from the last scene.
- Check the first word of every line. Starting a clip mid-word is the commonest bug, so start line clips at source frame 0 unless the lead-in is silence.

## Sound-design restraint
- Minimal sound effects. A bed that swells or pops under quiet intros distracts from the whispers.
- Normalize a music track's own loudness drift (slow AGC) before ducking it.

## Final pass checklist
1. Transcribe the render (Whisper `medium`, tail segments isolated) and compare to the script.
2. Black-frame scan, frame count, duration, loudness per scene.
3. A contact sheet (one frame every 2 seconds) to scan continuity.
4. Open the file in QuickTime. Report every open issue plainly, even small ones.
