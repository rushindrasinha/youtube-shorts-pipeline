import React from "react";
import { Composition } from "remotion";
import { CaptionOverlay } from "./CaptionOverlay";
import { z } from "zod";

export const CaptionOverlaySchema = z.object({
  captionsJsonFile: z.string(),
  durationMs: z.number(),
});

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="CaptionOverlay"
      component={CaptionOverlay}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={30 * 60}
      defaultProps={{
        captionsJsonFile: "captions.json",
        durationMs: 60000,
      }}
      schema={CaptionOverlaySchema}
      calculateMetadata={async ({ props }) => ({
        durationInFrames: Math.ceil((props.durationMs / 1000) * 30),
      })}
    />
  );
};
