import { useState } from "react";
import { Button } from "../components/Button";
import { Notice } from "../components/Notice";
import { Skeleton } from "../components/Skeleton";
import { Toggle } from "../components/Toggle";
import { navigate } from "../router";
import { useMirrorActions, useMirrorState } from "../store";

export function Welcome() {
  const { status, error, salonName, retained, tombstoned } = useMirrorState();
  const { reload, setRetained, deleteEverything } = useMirrorActions();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (status === "loading") return <Skeleton lines={5} label="Opening Mirror" />;

  if (status === "deleted") {
    return (
      <Notice tone="ok" title="Everything deleted.">
        <p>
          {tombstoned} consultation{tombstoned === 1 ? "" : "s"} tombstoned. Your scans, renders and
          consents are gone from this salon's records.
        </p>
      </Notice>
    );
  }

  if (status === "error") {
    return (
      <Notice tone="error" title="Mirror could not open." action={{ label: "Try again", onClick: reload }}>
        <p>{error}</p>
      </Notice>
    );
  }

  const onDelete = async () => {
    setDeleting(true);
    try {
      await deleteEverything();
    } finally {
      setDeleting(false);
    }
  };

  return (
    <section className="welcome">
      <h1 className="welcome-salon">{salonName}</h1>
      <p className="welcome-line">Sit. Scan. See.</p>
      <Button className="welcome-cta" onClick={() => navigate("capture")}>
        Start your scan
      </Button>
      <p className="welcome-privacy">
        Your selfie is processed and deleted after rendering unless you keep it for progress
        tracking.
      </p>
      <Toggle
        id="retention"
        label="Keep my scans for progress tracking"
        checked={retained}
        onChange={(value) => void setRetained(value)}
      />
      {confirming ? (
        <div className="welcome-confirm" role="group" aria-label="Confirm deletion">
          <p>Delete every scan, render, consent and plan for you at this salon?</p>
          <div className="welcome-confirm-actions">
            <Button variant="secondary" onClick={() => setConfirming(false)} disabled={deleting}>
              Keep
            </Button>
            <Button onClick={() => void onDelete()} disabled={deleting}>
              {deleting ? "Deleting" : "Delete everything"}
            </Button>
          </div>
        </div>
      ) : (
        <Button variant="link" onClick={() => setConfirming(true)}>
          Delete everything now
        </Button>
      )}
    </section>
  );
}
