import type { ReactNode } from "react";
import { routeLabels, routes, useRoute } from "../router";
import { useMirrorState } from "../store";

export interface ScreenProps {
  children: ReactNode;
}

export function Screen({ children }: ScreenProps) {
  const route = useRoute();
  const { salonName, status } = useMirrorState();
  return (
    <div className="mirror">
      <header className="mirror-header">
        <p className="mirror-salon">{salonName || "Chairside"}</p>
        <p className="mirror-step">{routeLabels[route]}</p>
      </header>
      <main className="mirror-body" id="main">
        {children}
      </main>
      {status === "ready" && (
        <nav className="step-nav" aria-label="Consultation steps">
          {routes.map((r) => (
            <a
              key={r}
              className="step-link"
              href={`#/${r}`}
              aria-current={r === route ? "step" : undefined}
            >
              {routeLabels[r]}
            </a>
          ))}
        </nav>
      )}
    </div>
  );
}
