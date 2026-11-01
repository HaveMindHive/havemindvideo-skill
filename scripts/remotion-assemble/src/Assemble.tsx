import { AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// One shot, all in frames at the composition fps (assemble.py computes these).
export type Shot = {
  id: string;
  video: string;
  video_in: number; // source in-point (dead air trimmed)
  frames: number; // base length on the timeline; the next shot starts after this
  tail: number; // extra picture frames shown under the next shot's dissolve
  fade_in: number; // dissolve frames from the previous shot (0 = hard cut)
  audio: string | null; // baked, levelled voice for this shot
  audio_in: number;
  dialogue: boolean;
};
export type AssembleProps = {
  fps: number;
  aspect_ratio: string;
  shots: Shot[];
  music?: string | null;
  music_volume?: number; // level in shots with no dialogue; ducked to 40% under dialogue
};

const RAMP = 8; // frames for music duck ramps

// Hard cuts or dissolves in shot-list order. Video is always muted; each shot's
// voice plays only for its base length so it never bleeds into the next shot.
// OffthreadVideo, never Video: Video jitters on render.
export const Assemble: React.FC<AssembleProps> = ({ shots, music, music_volume = 0.5 }) => {
  const { durationInFrames } = useVideoConfig();
  let at = 0;
  const placed = shots.map((s) => {
    const from = at;
    at += s.frames;
    return { ...s, from };
  });

  const level = (f: number) => {
    const i = placed.findIndex((s) => f >= s.from && f < s.from + s.frames);
    const lvl = (s?: Shot) => (s?.dialogue ? music_volume * 0.4 : music_volume);
    if (i < 0) return lvl(placed[placed.length - 1]);
    const cur = lvl(placed[i]);
    const prev = i > 0 ? lvl(placed[i - 1]) : cur;
    return interpolate(f - placed[i].from, [0, RAMP], [prev, cur], { extrapolateRight: "clamp" });
  };

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {placed.map((s) => (
        <Sequence key={s.id} from={s.from} durationInFrames={s.frames + s.tail}>
          <ShotPicture shot={s} />
          {s.audio && (
            <Sequence durationInFrames={s.frames}>
              <Audio src={staticFile(s.audio)} trimBefore={s.audio_in} />
            </Sequence>
          )}
        </Sequence>
      ))}
      {music && (
        <Audio
          src={staticFile(music)}
          loop
          volume={(f) =>
            level(f) *
            interpolate(f, [0, 15, durationInFrames - 30, durationInFrames], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          }
        />
      )}
    </AbsoluteFill>
  );
};

const ShotPicture: React.FC<{ shot: Shot }> = ({ shot }) => {
  const frame = useCurrentFrame();
  const opacity = shot.fade_in ? interpolate(frame, [0, shot.fade_in], [0, 1], { extrapolateRight: "clamp" }) : 1;
  return (
    <AbsoluteFill style={{ opacity }}>
      <OffthreadVideo
        src={staticFile(shot.video)}
        trimBefore={shot.video_in}
        muted
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
    </AbsoluteFill>
  );
};
