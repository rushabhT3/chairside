import { useState } from "react";
import { addWeeks, formatCents, formatDate } from "../../lib/format";
import type { PlanItem } from "../../lib/snapshot";
import { Button } from "../components/Button";
import { Notice } from "../components/Notice";
import { Skeleton } from "../components/Skeleton";
import { navigate } from "../router";
import { useMirrorActions, useMirrorState } from "../store";

function ItemList({ title, items }: { title: string; items: PlanItem[] }) {
  if (items.length === 0) return null;
  return (
    <section className="plan-group" aria-label={title}>
      <h2 className="ticket-heading">{title}</h2>
      <ul className="plan-items">
        {items.map((item) => (
          <li key={item.code} className="plan-item">
            <span className="plan-item-name">
              {item.name}
              {item.qty > 1 ? ` × ${item.qty}` : ""}
            </span>
            <span className="plan-item-price">{formatCents(item.price_cents * item.qty)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Plan() {
  const { status, consultation, accepted } = useMirrorState();
  const { acceptPlan } = useMirrorActions();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status !== "ready" || !consultation) return <Skeleton lines={7} label="Loading your plan" />;

  const plan = consultation.plan;
  if (!plan) return <Notice title="No plan yet." action={{ label: "Scan first", onClick: () => navigate("capture") }} />;

  const rebook = formatDate(addWeeks(consultation.started_at, plan.rebook_weeks));

  const onAccept = async () => {
    setBusy(true);
    setError(null);
    try {
      await acceptPlan();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not accept the plan.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="plan">
      <h1 className="consent-title">Your plan</h1>
      <ItemList title="Services" items={plan.services} />
      <ItemList title="Products" items={plan.products} />
      <p className="plan-total">
        <span>Total</span>
        <span className="plan-total-amount">{formatCents(plan.total_cents)}</span>
      </p>
      <p className="plan-rebook">Come back around {rebook}, in {plan.rebook_weeks} weeks.</p>
      {error && <Notice tone="error" title={error} />}
      {accepted ? (
        <div className="accepted" role="status">
          <p className="accepted-line">Accepted · {consultation.stylist} confirms on Floor.</p>
          <Button variant="secondary" onClick={() => navigate("return")}>
            See what changed since last time
          </Button>
        </div>
      ) : (
        <Button onClick={() => void onAccept()} disabled={busy}>
          {busy ? "Accepting" : "Accept plan"}
        </Button>
      )}
    </section>
  );
}
