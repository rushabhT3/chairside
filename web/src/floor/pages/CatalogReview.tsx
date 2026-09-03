import { useEffect, useRef, useState } from "react";
import { ConfidenceChip } from "../components/Chips";
import { PageHeader } from "../components/PageHeader";
import { Empty, WithSnapshot } from "../components/States";
import { href } from "../router";
import type { SnapshotState } from "../useSnapshot";
import type { ExtractionField, ExtractionRow } from "../../lib/snapshot";

const VIEWER_BASE_URL = import.meta.env.VITE_NUTRIENT_BASE_URL ?? "https://cdn.cloud.pspdfkit.com/pspdfkit-web@1.21.0/";
const CONFIDENCE_THRESHOLD = 0.85;
const A4 = { width: 595, height: 842 };
const ACCENT_RGB = { r: 90, g: 31, b: 31 };
const STROKE_WIDTH = 2;

type ViewerStatus = "idle" | "loading" | "ready" | "error";

function documentUrl(row: ExtractionRow): string | null {
  return row.source === "price_list" ? "/seed/price_list.pdf" : null;
}

function useNutrientViewer(container: React.RefObject<HTMLDivElement | null>, url: string | null, fields: ExtractionField[]) {
  const [status, setStatus] = useState<ViewerStatus>(url ? "loading" : "idle");
  const [message, setMessage] = useState("");
  useEffect(() => {
    const el = container.current;
    if (!url || !el) return;
    let disposed = false;
    let unload: (() => void) | null = null;
    setStatus("loading");
    import("@nutrient-sdk/viewer")
      .then(async (mod) => {
        const NutrientViewer = mod.default;
        if (disposed) return;
        const instance = await NutrientViewer.load({ container: el, document: url, baseUrl: VIEWER_BASE_URL });
        if (disposed) {
          NutrientViewer.unload(el);
          return;
        }
        unload = () => NutrientViewer.unload(el);
        await Promise.all(
          fields.map((f) =>
            instance.create(
              new NutrientViewer.Annotations.RectangleAnnotation({
                pageIndex: f.page - 1,
                boundingBox: new NutrientViewer.Geometry.Rect({ left: f.bbox[0], top: f.bbox[1], width: f.bbox[2], height: f.bbox[3] }),
                strokeColor: new NutrientViewer.Color(ACCENT_RGB),
                strokeWidth: STROKE_WIDTH,
              }),
            ),
          ),
        );
        setStatus("ready");
      })
      .catch((error: unknown) => {
        if (disposed) return;
        setStatus("error");
        setMessage(error instanceof Error ? error.message : String(error));
      });
    return () => {
      disposed = true;
      unload?.();
    };
  }, [container, url, fields]);
  return { status, message };
}

function PageOutline({ fields }: { fields: ExtractionField[] }) {
  return (
    <svg className="page-outline" viewBox={`0 0 ${A4.width} ${A4.height}`} role="img" aria-label="Citation positions on the page">
      {fields.map((f) => (
        <rect key={f.name} className={f.confidence < CONFIDENCE_THRESHOLD ? "page-outline__box page-outline__box--low" : "page-outline__box"} x={f.bbox[0]} y={f.bbox[1]} width={f.bbox[2]} height={f.bbox[3]} />
      ))}
    </svg>
  );
}

function ReviewBody({ row }: { row: ExtractionRow }) {
  const container = useRef<HTMLDivElement>(null);
  const url = documentUrl(row);
  const [fields, setFields] = useState(row.fields);
  const [status, setStatus] = useState(row.status);
  const [editing, setEditing] = useState(false);
  const viewer = useNutrientViewer(container, url, row.fields);
  const lowest = Math.min(...fields.map((f) => f.confidence));
  return (
    <>
      <PageHeader
        kicker={`${row.source} · ${row.file}`}
        title={row.id}
        lede="Nutrient DWS extracted these fields with per-field confidence and citations. Confirm what is right; edit what is not. Nothing is accepted silently."
        actions={
          <a className="button button--quiet" href={href({ page: "catalog" })}>
            Back to catalog
          </a>
        }
      />
      <div className="review">
        <div className="viewer" aria-busy={viewer.status === "loading"}>
          <div ref={container} className="viewer__container" />
          {viewer.status === "loading" && <div className="viewer__state">Loading the document in the Nutrient Viewer…</div>}
          {viewer.status === "error" && <div className="viewer__state">The Viewer could not load ({viewer.message}). The citation outline on the right still shows where every field was read.</div>}
          {viewer.status === "idle" && <div className="viewer__state">Source image is not served in judge mode; the outline shows the citations.</div>}
        </div>
        <div className="citations">
          <div className="section__head">
            <h2>Citations</h2>
            <ConfidenceChip confidence={lowest} />
          </div>
          <PageOutline fields={fields} />
          <ul className="fields">
            {fields.map((f, i) => (
              <li key={f.name} className="fields__item">
                <span className="fields__name mono">{f.name}</span>
                {editing ? (
                  <label className="field">
                    <span className="visually-hidden">{f.name}</span>
                    <input className="field__input" value={f.value} onChange={(e) => setFields(fields.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))} />
                  </label>
                ) : (
                  <span>{f.value}</span>
                )}
                <ConfidenceChip confidence={f.confidence} />
              </li>
            ))}
          </ul>
          <div className="review__actions" role="group" aria-label="Review decision">
            <button type="button" className="button button--primary" disabled={status === "confirmed"} onClick={() => { setEditing(false); setStatus("confirmed"); }}>
              Confirm
            </button>
            <button type="button" className="button" aria-pressed={editing} onClick={() => setEditing((e) => !e)}>
              {editing ? "Done editing" : "Edit"}
            </button>
            <button type="button" className="button" disabled={status === "rejected"} onClick={() => { setEditing(false); setStatus("rejected"); }}>
              Reject
            </button>
          </div>
          <p className={status === "pending" ? "status" : status === "confirmed" ? "status status--ok" : "status status--err"} role="status">
            <span className={status === "pending" ? "dot dot--warn" : status === "confirmed" ? "dot dot--ok" : "dot dot--err"} aria-hidden="true" />
            {status === "pending" ? "Pending human confirmation" : status === "confirmed" ? "Confirmed · will be included in the sealed catalog" : "Rejected · excluded from the catalog"}
          </p>
        </div>
      </div>
    </>
  );
}

export function CatalogReview({ id, snapshot }: { id: string; snapshot: SnapshotState }) {
  return (
    <WithSnapshot snapshot={snapshot} label="Loading extraction">
      {(data) => {
        const row = data.extractions.find((e) => e.id === id);
        if (!row) {
          return (
            <>
              <PageHeader kicker="Catalog" title="Row not found" />
              <Empty>{`No extraction row ${id}.`}</Empty>
            </>
          );
        }
        return <ReviewBody key={row.id} row={row} />;
      }}
    </WithSnapshot>
  );
}
