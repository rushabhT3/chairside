import { useCallback, useState } from "react";
import { dataMode } from "../../lib/data";
import { formatTime, shortHash } from "../../lib/format";
import type { TreatmentClass } from "../../lib/snapshot";
import { Button } from "../components/Button";
import { Notice } from "../components/Notice";
import { SigningSheet } from "../components/SigningSheet";
import { Skeleton } from "../components/Skeleton";
import { navigate } from "../router";
import { useMirrorActions, useMirrorState } from "../store";

const plainLanguage: Record<TreatmentClass, string> = {
  chemical: "Colour and other chemical services",
  heat: "Heat styling and smoothing",
  injectable: "Injectable treatments",
  laser: "Laser treatments",
  none: "Facial and cosmetic services",
};

const fixtureSessionUrl = "./sign-fixture.html";
const ledgerUrl = "../floor/#/ledger";

export function Consent() {
  const { status, consultation, signedAt } = useMirrorState();
  const { markSigned } = useMirrorActions();
  const [open, setOpen] = useState(false);

  const onSigned = useCallback(
    (at: string) => {
      markSigned(at);
      setOpen(false);
    },
    [markSigned],
  );
  const onClose = useCallback(() => setOpen(false), []);

  if (status !== "ready" || !consultation) return <Skeleton lines={5} label="Preparing consent" />;

  const consent = consultation.consent;
  if (!consent) {
    return (
      <Notice title="No consent needed yet." action={{ label: "See your plan", onClick: () => navigate("plan") }}>
        <p>Your plan has no treatment that needs a signature.</p>
      </Notice>
    );
  }

  const sessionUrl =
    dataMode() === "live" && consent.envelope.session_url ? consent.envelope.session_url : fixtureSessionUrl;
  const classes = consent.treatment_classes.filter((c) => c !== "none");

  return (
    <section className="consent">
      <h1 className="consent-title">What you are agreeing to</h1>
      <ul className="consent-classes">
        {(classes.length ? classes : consent.treatment_classes).map((cls) => (
          <li key={cls} className="consent-class">
            {plainLanguage[cls]}
          </li>
        ))}
      </ul>
      <p className="consent-copy">
        The form was generated for these treatments, your declared allergens and French law. Read
        it in the signing sheet before you sign.
      </p>

      {signedAt ? (
        <div className="sealed" role="status">
          <p className="sealed-line">
            Sealed · hash {shortHash(consent.envelope.sealed_hash)} ·{" "}
            <a className="sealed-verify" href={ledgerUrl}>
              Verify
            </a>
          </p>
          <p className="sealed-when">Signed {formatTime(signedAt)} on this phone.</p>
          <Button onClick={() => navigate("plan")}>See your plan</Button>
        </div>
      ) : (
        <Button onClick={() => setOpen(true)}>Review and sign</Button>
      )}

      <SigningSheet open={open} sessionUrl={sessionUrl} onSigned={onSigned} onClose={onClose} />
    </section>
  );
}
