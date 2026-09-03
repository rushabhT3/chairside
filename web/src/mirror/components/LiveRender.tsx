import { useEffect, useMemo, useState } from "react";
import { renderHairColour } from "../../lib/renderProxy";
import type { ShadeEntry } from "../../lib/snapshot";
import { BeforeAfter } from "./BeforeAfter";
import { Notice } from "./Notice";
import { Skeleton } from "./Skeleton";

export interface LiveRenderProps {
  scan: Blob;
  shade: ShadeEntry;
}

type Phase = { kind: "rendering" } | { kind: "ready"; url: string } | { kind: "failed"; message: string };

export function LiveRender({ scan, shade }: LiveRenderProps) {
  const [phase, setPhase] = useState<Phase>({ kind: "rendering" });
  const beforeUrl = useMemo(() => URL.createObjectURL(scan), [scan]);

  useEffect(() => () => URL.revokeObjectURL(beforeUrl), [beforeUrl]);

  useEffect(() => {
    let cancelled = false;
    setPhase({ kind: "rendering" });
    renderHairColour(scan, shade.hex)
      .then((url) => {
        if (!cancelled) setPhase({ kind: "ready", url });
      })
      .catch((error: Error) => {
        if (!cancelled) setPhase({ kind: "failed", message: error.message });
      });
    return () => {
      cancelled = true;
    };
  }, [scan, shade.hex]);

  if (phase.kind === "rendering") return <Skeleton lines={4} label={`Rendering ${shade.code} on your scan`} />;
  if (phase.kind === "failed") {
    return (
      <Notice tone="quiet" title="Your scan could not be rendered.">
        <p>{phase.message}</p>
      </Notice>
    );
  }
  return (
    <>
      <BeforeAfter beforeUrl={beforeUrl} afterUrl={phase.url} label={`${shade.code} ${shade.name}`} />
      <p className="render-footer">Rendered from your own scan by YouCam · this device only</p>
    </>
  );
}
