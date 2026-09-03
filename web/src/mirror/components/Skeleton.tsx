export interface SkeletonProps {
  lines?: number;
  label?: string;
}

const defaultLines = 4;

export function Skeleton({ lines = defaultLines, label = "Loading" }: SkeletonProps) {
  return (
    <div className="skeleton" role="status" aria-label={label}>
      {Array.from({ length: lines }, (_, i) => (
        <span key={i} className="skeleton-line" />
      ))}
    </div>
  );
}
