import type { ReactNode } from "react";
import type { SnapshotState } from "../useSnapshot";
import type { Snapshot } from "../../lib/snapshot";

const SKELETON_LINES = 5;

export function Loading({ label }: { label: string }) {
  return (
    <div className="skeleton" role="status" aria-live="polite" aria-label={label}>
      {Array.from({ length: SKELETON_LINES }, (_, i) => (
        <div key={i} className={i === SKELETON_LINES - 1 ? "skeleton__line skeleton__line--short" : "skeleton__line"} />
      ))}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="status status--err" role="alert">
      <span className="dot dot--err" aria-hidden="true" />
      <span>Could not load Floor data. {message}</span>
    </div>
  );
}

export function Empty({ children }: { children: string }) {
  return <p className="empty">{children}</p>;
}

export function WithSnapshot({
  snapshot,
  label,
  children,
}: {
  snapshot: SnapshotState;
  label: string;
  children: (data: Snapshot) => ReactNode;
}) {
  if (snapshot.status === "loading") return <Loading label={label} />;
  if (snapshot.status === "error") return <ErrorState message={snapshot.message} />;
  return <>{children(snapshot.data)}</>;
}
