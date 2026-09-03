import type { CSSProperties } from "react";
import type { ShadeEntry } from "../../lib/snapshot";

export interface ShadeChipProps {
  shade: ShadeEntry;
  selected: boolean;
  rendered: boolean;
  onSelect: (shade: ShadeEntry) => void;
}

export function ShadeChip({ shade, selected, rendered, onSelect }: ShadeChipProps) {
  const swatch = { "--swatch": shade.hex } as CSSProperties;
  return (
    <button
      type="button"
      className="chip"
      aria-pressed={selected}
      data-rendered={rendered}
      onClick={() => onSelect(shade)}
    >
      <span className="chip-swatch" style={swatch} aria-hidden="true" />
      <span className="chip-code">{shade.code}</span>
      <span className="chip-name">{shade.name}</span>
    </button>
  );
}
