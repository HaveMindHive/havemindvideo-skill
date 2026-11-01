import { Composition } from "remotion";
import { Assemble, AssembleProps } from "./Assemble";

const SIZES: Record<string, [number, number]> = {
  "9:16": [1080, 1920],
  "16:9": [1920, 1080],
  "1:1": [1080, 1080],
  "4:5": [1080, 1350],
};

export const Root: React.FC = () => (
  <Composition
    id="Assemble"
    component={Assemble}
    defaultProps={{ fps: 30, aspect_ratio: "9:16", shots: [] } as AssembleProps}
    // Size, fps and length all come from the props assemble.py writes.
    calculateMetadata={({ props }) => {
      const [width, height] = SIZES[props.aspect_ratio] ?? SIZES["9:16"];
      const durationInFrames = Math.max(1, props.shots.reduce((n, s) => n + s.frames, 0));
      return { width, height, fps: props.fps, durationInFrames };
    }}
  />
);
