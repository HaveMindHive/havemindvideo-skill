import { AbsoluteFill, Audio, OffthreadVideo, Series, interpolate, staticFile, useVideoConfig } from "remotion";

export type Shot = { id: string; video: string; audio: string | null; frames: number };
export type AssembleProps = {
  fps: number;
  aspect_ratio: string;
  shots: Shot[];
  music?: string | null;
  music_volume?: number;
};

// Hard cuts in shot-list order. A shot's own audio plays (lipsync clip audio,
// or a separate narration file with the clip muted). Optional music bed under all.
// OffthreadVideo, never Video: Video jitters on render.
export const Assemble: React.FC<AssembleProps> = ({ shots, music, music_volume = 0.25 }) => {
  const { fps, durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <Series>
        {shots.map((s) => (
          <Series.Sequence key={s.id} durationInFrames={s.frames}>
            <OffthreadVideo
              src={staticFile(s.video)}
              muted={!!s.audio}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
            {s.audio && <Audio src={staticFile(s.audio)} />}
          </Series.Sequence>
        ))}
      </Series>
      {music && (
        <Audio
          src={staticFile(music)}
          loop
          volume={(f) =>
            music_volume *
            interpolate(f, [0, fps, durationInFrames - fps, durationInFrames], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          }
        />
      )}
    </AbsoluteFill>
  );
};
