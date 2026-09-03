export interface StepItem {
  name: string;
  status: "pending" | "running" | "done";
  ts: string | null;
}

export interface StepListProps {
  steps: StepItem[];
}

export function StepList({ steps }: StepListProps) {
  return (
    <ol className="steps" aria-live="polite">
      {steps.map((step) => (
        <li key={step.name} className="step" data-status={step.status}>
          <span className="step-name">{step.name}</span>
          <span className="step-ts">{step.ts ?? ""}</span>
        </li>
      ))}
    </ol>
  );
}
