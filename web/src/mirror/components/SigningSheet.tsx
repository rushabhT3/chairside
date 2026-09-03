import { useEffect } from "react";

export interface SigningSheetProps {
  open: boolean;
  sessionUrl: string;
  onSigned: (signedAt: string) => void;
  onClose: () => void;
}

interface SignedMessage {
  type: "chairside.signed";
  signed_at: string;
}

function isSignedMessage(data: unknown): data is SignedMessage {
  return (
    typeof data === "object" &&
    data !== null &&
    (data as { type?: unknown }).type === "chairside.signed" &&
    typeof (data as { signed_at?: unknown }).signed_at === "string"
  );
}

export function SigningSheet({ open, sessionUrl, onSigned, onClose }: SigningSheetProps) {
  useEffect(() => {
    if (!open) return;
    const onMessage = (event: MessageEvent<unknown>) => {
      if (isSignedMessage(event.data)) onSigned(event.data.signed_at);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("message", onMessage);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("message", onMessage);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onSigned, onClose]);

  if (!open) return null;

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <section
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-label="Signing session"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="sheet-header">
          <p className="sheet-title">Sign on this phone</p>
          <button type="button" className="btn btn-link" onClick={onClose}>
            Close
          </button>
        </header>
        <iframe className="sheet-frame" src={sessionUrl} title="Signing session" />
      </section>
    </div>
  );
}
