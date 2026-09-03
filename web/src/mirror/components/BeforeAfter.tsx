import { useState } from "react";
import type { CSSProperties } from "react";
import { assetUrl } from "../../lib/assetUrl";

export interface BeforeAfterProps {
  beforeUrl: string;
  afterUrl: string;
  label: string;
}

const initialSplit = 50;
const keyboardStep = 4;

export function BeforeAfter({ beforeUrl, afterUrl, label }: BeforeAfterProps) {
  const [split, setSplit] = useState(initialSplit);
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div className="ba ba-missing" role="img" aria-label={`${label}: render unavailable`}>
        <span className="ba-missing-label">{label}</span>
        <span className="ba-missing-copy">Render not reachable on this device.</span>
      </div>
    );
  }

  const splitStyle = { "--split": `${split}%` } as CSSProperties;

  return (
    <div className="ba" style={splitStyle}>
      <img className="ba-before" src={assetUrl(beforeUrl)} alt="Before" onError={() => setFailed(true)} />
      <div className="ba-after-clip" aria-hidden="true">
        <img className="ba-after" src={assetUrl(afterUrl)} alt="" onError={() => setFailed(true)} />
      </div>
      <span className="ba-handle" aria-hidden="true" />
      <input
        className="ba-slider"
        type="range"
        min={0}
        max={100}
        step={keyboardStep}
        value={split}
        aria-label={`${label}: before and after`}
        aria-valuetext={`${split}% after`}
        onChange={(event) => setSplit(Number(event.target.value))}
      />
      <span className="ba-tag ba-tag-before">Before</span>
      <span className="ba-tag ba-tag-after">After</span>
    </div>
  );
}
