import type { CSSProperties } from "react";

export interface ConcernBarProps {
  label: string;
  score: number;
  inverted?: boolean;
}

export function ConcernBar({ label, score, inverted = false }: ConcernBarProps) {
  const fill = { "--fill": `${score}%` } as CSSProperties;
  return (
    <div className="concern">
      <span className="concern-label">{label}</span>
      <span className="concern-track" aria-hidden="true">
        <span className={`concern-fill ${inverted ? "concern-fill-good" : ""}`.trim()} style={fill} />
      </span>
      <span className="concern-score" aria-label={`${label} ${score} of 100`}>
        {score}
      </span>
    </div>
  );
}
