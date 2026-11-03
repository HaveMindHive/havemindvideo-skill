# Prompting Kling 3.0 + lipsync-2-pro: get it right the first take

Read this before EVERY paid video render. Written 11-02-2026 from (1) the Stop Swiping
post-mortem (90 video renders, 20 used; ~22 h for a 2-min ad), (2) sync.so's and Replicate's
docs, (3) third-party repos cloned in ~/HaveMindHive/research/video-prompting/ (smixs/visual-skills
kling.md, OSideMedia/higgsfield-ai-prompt-skill, Yuyyxz/kling-prompt-engineering, guyow/video-studio,
VideoVerses/Cuti-Harness, Rylaispirit/cinematic-video-prompt-skill). Post-mortem:
~/HaveMindHive/research/stop-swiping-postmortem.md.

## The two mistakes that cost the most

1. **Telling Kling "mouth closed / no talking" on a clip that will be lip-synced.**
   sync.so: lipsync-2/-pro "require natural speaking motion in the input video"; still segments
   get NO lip-sync "even if audio is present"; for AI video add "the character should be speaking
   naturally". (https://sync.so/docs/models, https://sync.so/docs/compatibility-and-tips/media-content-tips.md)
   - Talking clip: start picture has a relaxed CLOSED mouth (stops toothy first frames), prompt says
     she is **talking naturally with small mouth movements**. Never put `talking` in the negative.
   - Reaction clip (no line): here "lips stay together" is right.
2. **Rendering from a start picture nobody checked.** 14 video takes died on bad stills (7-finger hand,
   open mouth, a stranger's shoulder, wrong gaze). Pre-flight below is mandatory.

## Pre-flight (before paying for any video)
Make a 512px sheet of the start (and end) image and check, writing the answers in STATUS.md:
- [ ] Same person as the locked character (face, hair, outfit)
- [ ] **Congruent with the shots around it.** Put the start picture in ONE sheet next to the last
      frame of the shot before and the first frame of the shot after (`ffmpeg ... tile=3x1`,
      512 px). Same set and background, same lighting direction and color/grade, same wardrobe,
      hair, nails, jewelry, same props (cup, phone model and case), same time of day, same side of
      the table / screen direction. Any mismatch: fix the picture (pass the scene reference and the
      neighbour frame as image inputs) before paying for video. See character-consistency.md.
- [ ] 5 fingers on every visible hand; hands rest on/hold an object (phone, cup, pot)
- [ ] Nobody else's head/shoulder/hand intruding; no text on screen except the real phone screen
- [ ] Mouth: closed and relaxed (talking AND reaction shots)
- [ ] Eyes point where the beat needs them (camera / phone / other person)
- [ ] 9:16, at least 1080 wide (Replicate ignores aspect_ratio when start_image is given)
- [ ] Vivi's notes for this shot written as a numbered checklist (e.g. "1. wide eyes on 'amazing' 2. slight head shake on 'so long' 3. closed-mouth smile at end"). Ambiguous note -> ask her, don't render.
- [ ] Duration = voice line length + ~1 s, rounded up (Kling takes 3-15 s integers). Never pad with a frozen frame.

## Prompt structure (image-to-video)
Write 4-7 short lines in this order. Describe only what CHANGES; the image is the identity anchor.
Re-describing the face makes image and text conflict and the model "picks a side".

```
Keep her face, hair, outfit and the room exactly as in the image. Only <what moves> moves.
0-2s: <one physical action>.
2-5s: <next action, physical words>.
5-7s: <final beat / end state>.
Camera: locked-off medium close-up, eye level, single continuous shot, no cuts.
Light: same light throughout.
```
- One main action + at most 2 small ones; at most 3 timed beats per 5-7 s.
- Expressions as muscles, not emotions: "corners of her mouth press up, lips stay together, cheeks
  lift slightly" (warm smile), "eyebrows lift, eyes widen" (wonder), "shakes her head twice, small".
- Restraint = positive statement + specific ban: "lips stay together" in the prompt AND `teeth,
  open mouth, grin` in the negative. Negative: 6-10 plain items, no "no ...", no generic quality words.
- Lock the camera on any face/speaking shot; every head turn or camera move hurts lip-sync and identity.
- Add 1-2 life cues so it isn't a mannequin: a blink, thumb moves on phone, a breath.
- Duration goes in the API `duration`, never in prose.

### Talking shot (will be lip-synced)
```
Keep the waitress's face, hair, uniform and the diner exactly as in the image.
0-1s: she looks straight into the lens, coffee pot held steady at her waist.
1-<N>s: she is talking warmly to the camera, speaking naturally with small relaxed mouth movements and a slight nod.
End: a small closed-lip smile.
Camera: locked-off medium close-up, eye level, face large and centred, single continuous shot.
```
Negative: `extra people, extra fingers, hand near face, profile view, face morph, big grin, camera movement, subtitles, text`
Then `gen_lipsync2pro.py` (cut_off, temperature 0.3; 0.5 if the mouth looks too stiff).

### Reaction shot (no line)
```
Keep her face, hair, blouse and the booth exactly as in the image. Only her expression and head move.
0-2s: she reads the phone held in both hands, eyes open and tracking the screen, one blink.
2-5s: she slowly shakes her head twice, small, eyebrows lifting, eyes still on the screen.
5-7s: the corners of her mouth press up into a soft smile, lips staying together, cheeks lifting.
Camera: locked-off medium close-up, eye level, single continuous shot.
```
Negative: `teeth, open mouth, grin, laughing, closed eyes, extra fingers, phone morphing, extra people, camera movement`

## End frames: use sparingly
Kling: big differences between start and end frames "may cause a lens switch"
(https://kling.ai/quickstart/ai-video-start-end-frames). Stop Swiping shot 13 v7: an end frame with
the head UP snapped into place at ~3 s in both takes. Use an end frame only when it differs from the
start by a micro-expression (same pose, gaze, framing). Otherwise direct the end state in text.

## Retakes: change one thing, and never the same defect twice
- Before the first take, decide the budget: 2 takes in parallel max.
- Check every take yourself against the numbered checklist BEFORE showing Vivi
  (`scripts/check_take.py` sheet + Whisper). If it fails, say which item failed; don't show it as good.
- Same defect twice = rewrite the prompt / fix the start image, don't re-roll.
- Acting right but mistimed: shift/trim the base clip and re-lip-sync (cheap) instead of a new render.

## Replicate facts (checked 11-02-2026)
- kwaivgi/kling-v3-video: prompt, negative_prompt, start_image, end_image, mode (standard 720p / pro
  1080p / 4k), duration 3-15, generate_audio, multi_prompt. No cfg_scale or seed on Replicate.
- sync/lipsync-2-pro: video, audio, sync_mode (default **loop**: always pass cut_off), temperature
  (default 0.5), active_speaker. Face rendered at 512x512; best when face is frontal, unobstructed.
- Normal times: Kling 3 pro 2-4.5 min, lipsync 1.5-2 min. Scripts cancel + retry once past 10/7 min
  (`scripts/replicate_job.py`). If both tries fail, tell the person; don't keep re-launching.
