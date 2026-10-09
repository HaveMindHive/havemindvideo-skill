# Remotion: captions, title cards, and overlays

Remotion is a React-based *programmatic* video compositor — you write components that render to video, you don't generate footage with it. It has no role in phases 2-6 of this pipeline (it can't generate a character or a scene). Its role is narrow and specific: **burned-in captions, title/end cards, and data-driven text overlays that Resolve + ffmpeg handle badly in this pipeline.**

## Why it's here at all

This pipeline's `ffmpeg` build typically lacks `drawtext`/`libass`, so burning in captions or lower-thirds via ffmpeg filters isn't available out of the box, and hand-placing text overlays per-shot in Resolve for something that's really a template (a consistent end-card format, caption styling that repeats every shot) is slower and less consistent than it should be. Remotion fixes both: it renders text as real React/CSS, driven by data, reproducibly, and exports straight to a video file you drop into the Resolve timeline like any other clip.

**It is not a replacement for phase 7's Resolve assembly.** Resolve is the right tool for shot-by-shot timeline assembly, audio sync, and the kind of "look at the cut and judge if it feels right" iteration that a GUI timeline is built for. Remotion is code — excellent for an exact, reproducible, parameterized element (the same caption style on every shot, the same end-card layout every time), bad for freeform editorial judgment. Use it to produce specific overlay/title clips, then bring those into the Resolve assembly like any other asset.

The one exception: if a project has no DaVinci Resolve available at all (headless CI, no license/app installed), Remotion's `renderMedia()` can do full programmatic assembly — concatenating shot clips, placing audio, applying transitions — with no GUI app required. That's a real fallback path, not the default one; the rest of this pipeline assumes Resolve is available and documents that as primary.

## Setup

```bash
npx create-video@latest my-video-captions
cd my-video-captions
npm start        # opens Remotion Studio for live preview
```

This scaffolds a project with `src/Root.tsx` (where compositions are registered via `registerRoot()`) and `src/*.tsx` component files. Core primitives: `<AbsoluteFill>` for a full-frame layer, `<Sequence>` for timing one element within the overall duration, `useCurrentFrame()` + `interpolate()` for animation (don't use CSS transitions — Remotion renders frame-by-frame, not in real time, so CSS transition timing doesn't apply the way it would in a browser).

## Driving a composition from `shotlist.json`

This is the useful part for an agent-driven pipeline: Remotion compositions take **input props from a JSON file or JSON string**, so you don't hand-write a new React component per shot — one composition reads the shot list and generates every caption/title.

```bash
npx remotion render CaptionOverlay --props=./shotlist.json out/captions.mp4
```

```tsx
// src/CaptionOverlay.tsx
import {AbsoluteFill, Sequence, useCurrentFrame, interpolate, getInputProps} from 'remotion';

type Shot = {
  id: string;
  dialogue: string | null;
  duration_s: number;
};

type ShotList = {fps: number; shots: Shot[]};

export const CaptionOverlay: React.FC = () => {
  const {fps, shots} = getInputProps() as unknown as ShotList;
  let startFrame = 0;

  return (
    <AbsoluteFill>
      {shots.map((shot) => {
        const durationInFrames = Math.round(shot.duration_s * fps);
        const from = startFrame;
        startFrame += durationInFrames;
        if (!shot.dialogue) return null;

        return (
          <Sequence key={shot.id} from={from} durationInFrames={durationInFrames}>
            <Caption text={shot.dialogue} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

const Caption: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 120}}>
      <div style={{opacity, background: 'rgba(0,0,0,0.6)', color: 'white', padding: '12px 24px', borderRadius: 8, fontSize: 48, maxWidth: '80%', textAlign: 'center'}}>
        {text}
      </div>
    </AbsoluteFill>
  );
};
```

This reads `shotlist.json` directly — the same manifest the rest of the pipeline already produces and updates (see `references/shotlist-format.md`) — so there's no separate caption data entry step. Render it transparent (`--codec=vp8` or a ProRes-with-alpha codec) if you want to composite it as an overlay track in Resolve rather than a burned-in final export.

## Transitions and crossfades (if assembling in Remotion directly)

`@remotion/transitions` provides `TransitionSeries` for crossfades, slides, wipes, and custom GLSL-shader transitions between scenes:

```tsx
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';

<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={120}>
    <ShotA />
  </TransitionSeries.Sequence>
  <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 15})} />
  <TransitionSeries.Sequence durationInFrames={120}>
    <ShotB />
  </TransitionSeries.Sequence>
</TransitionSeries>
```

Only relevant if using Remotion for full assembly (the no-Resolve fallback path above) — the primary pipeline does cuts/transitions in Resolve.

## Captions from an audio transcript

`@remotion/captions` + `@remotion/install-whisper-cpp` can transcribe a dialogue audio file and auto-generate caption timing, rather than hand-typing timing offsets — useful if a project needs SRT export or caption timing more precise than "one caption per shot." For this pipeline's purposes, the per-shot manifest-driven approach above is usually enough (each shot already has exact `dialogue` text and `duration_s`); reach for Whisper-based transcription when caption timing needs to match speech sub-shot (word-by-word highlighting, karaoke-style captions), not for the basic "show this line during this shot" case.

## Rendering the final file

```bash
npx remotion render CaptionOverlay out/captions.mp4 --props=./shotlist.json
```

Or programmatically via `renderMedia()` from `@remotion/renderer` (Node.js/Bun) if driving the render from a script rather than the CLI — same props-in, file-out shape.
