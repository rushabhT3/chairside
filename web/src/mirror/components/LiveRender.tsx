import { useEffect, useMemo, useState } from "react";
import { renderScanOnce, type RenderRequest } from "../../lib/renderProxy";
import { BeforeAfter } from "./BeforeAfter";
import { Notice } from "./Notice";
import { Skeleton } from "./Skeleton";

export interface LiveRenderProps {
  scanId: string;
  scan: Blob;
  request: RenderRequest;
  label: string;
}

type Phase = { kind: "rendering" } | { kind: "ready"; url: string } | { kind: "failed"; message: string };

export function LiveRender({ scanId, scan, request, label }: LiveRenderProps) {
  const [phase, setPhase] = useState<Phase>({ kind: "rendering" });
  const beforeUrl = useMemo(() => URL.createObjectURL(scan), [scan]);
  const { kind, shade, template } = request;

  useEffect(() => () => URL.revokeObjectURL(beforeUrl), [beforeUrl]);

  useEffect(() => {
    let cancelled = false;
    setPhase({ kind: "rendering" });
    renderScanOnce(scanId, scan, { kind, shade, template })
      .then((url) => {
        if (!cancelled) setPhase({ kind: "ready", url });
      })
      .catch((error: Error) => {
        if (!cancelled) setPhase({ kind: "failed", message: error.message });
      });
    return () => {
      cancelled = true;
    };
  }, [scanId, scan, kind, shade, template]);

  if (phase.kind === "rendering") {
    return <Skeleton lines={4} label={`Rendering ${label} on your scan, about 15 seconds`} />;
  }
  if (phase.kind === "failed") {
    return (
      <Notice tone="quiet" title="Your scan could not be rendered.">
        <p>{phase.message}</p>
      </Notice>
    );
  }
  return (
    <>
      <BeforeAfter beforeUrl={beforeUrl} afterUrl={phase.url} label={label} />
      <p className="render-footer">Rendered from your own scan by YouCam · this device only</p>
    </>
  );
}
