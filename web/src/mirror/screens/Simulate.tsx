import { useState } from "react";
import { formatTime } from "../../lib/format";
import type { ShadeEntry, Simulation } from "../../lib/snapshot";
import { BeforeAfter } from "../components/BeforeAfter";
import { Button } from "../components/Button";
import { Notice } from "../components/Notice";
import { ShadeChip } from "../components/ShadeChip";
import { Skeleton } from "../components/Skeleton";
import { Tabs } from "../components/Tabs";
import { navigate } from "../router";
import { useMirrorState } from "../store";

type Tab = Simulation["tab"];

const tabs = [
  { id: "hair", label: "Hair" },
  { id: "skin", label: "Skin plan" },
  { id: "style", label: "Style" },
] as const;

function matchesShade(simulation: Simulation, shade: ShadeEntry): boolean {
  const byHex = simulation.hex?.toLowerCase() === shade.hex.toLowerCase();
  const byCode = simulation.sku_code?.endsWith(shade.code) ?? false;
  return byHex || byCode;
}

function RenderFooter({ simulation, note }: { simulation: Simulation; note: string }) {
  return (
    <p className="render-footer">
      Rendered {formatTime(simulation.as_of)} · {note} · this device only
    </p>
  );
}

export function Simulate() {
  const { status, consultation, shadeMap } = useMirrorState();
  const [tab, setTab] = useState<Tab>("hair");
  const [shade, setShade] = useState<ShadeEntry | null>(null);
  const [styleIndex, setStyleIndex] = useState(0);

  if (status !== "ready" || !consultation) return <Skeleton lines={6} label="Loading renders" />;

  const simulations = consultation.simulations.filter((s) => s.tab === tab);
  const hairRender = shade ? simulations.find((s) => matchesShade(s, shade)) : simulations[0];
  const activeShade =
    shade ?? shadeMap.find((entry) => hairRender && matchesShade(hairRender, entry)) ?? null;

  const renderHair = () => (
    <>
      <div className="chips" role="group" aria-label="Shades from the salon's line">
        {shadeMap.map((entry) => (
          <ShadeChip
            key={entry.code}
            shade={entry}
            selected={activeShade?.code === entry.code}
            rendered={simulations.some((s) => matchesShade(s, entry))}
            onSelect={setShade}
          />
        ))}
      </div>
      {hairRender ? (
        <>
          <BeforeAfter beforeUrl={hairRender.before_url} afterUrl={hairRender.after_url} label={hairRender.label} />
          <RenderFooter simulation={hairRender} note={activeShade?.code ?? hairRender.label} />
        </>
      ) : (
        <Notice title={`${activeShade?.code ?? "This shade"} is not rendered yet.`}>
          <p>Ask {consultation.stylist} to render it at the chair.</p>
        </Notice>
      )}
    </>
  );

  const renderList = (empty: string, selected: number, onSelect: (i: number) => void) => {
    const current = simulations[selected] ?? simulations[0];
    if (!current) return <Notice title={empty} />;
    return (
      <>
        {simulations.length > 1 && (
          <div className="chips" role="group" aria-label="Renders">
            {simulations.map((s, i) => (
              <button key={s.label} type="button" className="chip chip-text" aria-pressed={s === current} onClick={() => onSelect(i)}>
                {s.label}
              </button>
            ))}
          </div>
        )}
        <BeforeAfter beforeUrl={current.before_url} afterUrl={current.after_url} label={current.label} />
        <RenderFooter simulation={current} note={current.label} />
      </>
    );
  };

  return (
    <section className="simulate">
      <Tabs options={tabs} value={tab} onChange={setTab} label="What to simulate" />
      {tab === "hair" && renderHair()}
      {tab === "skin" && renderList("No skin plan rendered yet.", 0, () => undefined)}
      {tab === "style" && renderList("No styles rendered yet.", styleIndex, setStyleIndex)}
      <Button onClick={() => navigate("price")}>See prices</Button>
    </section>
  );
}
