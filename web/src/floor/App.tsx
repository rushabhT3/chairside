import { useCallback, useRef } from "react";
import { Rail } from "./components/Rail";
import { useKeyboardChords } from "./keyboard";
import { Attribution } from "./pages/Attribution";
import { Catalog } from "./pages/Catalog";
import { CatalogReview } from "./pages/CatalogReview";
import { Chairs } from "./pages/Chairs";
import { Consultation } from "./pages/Consultation";
import { Cost } from "./pages/Cost";
import { Ledger } from "./pages/Ledger";
import { Onboarding } from "./pages/Onboarding";
import { PriceWatch } from "./pages/PriceWatch";
import { useHashRoute, type Route } from "./router";
import { useSnapshot, type SnapshotState } from "./useSnapshot";

function Page({ route, snapshot }: { route: Route; snapshot: SnapshotState }) {
  switch (route.page) {
    case "consultation":
      return <Consultation id={route.id} snapshot={snapshot} />;
    case "catalog":
      return <Catalog snapshot={snapshot} />;
    case "catalog-review":
      return <CatalogReview id={route.id} snapshot={snapshot} />;
    case "price-watch":
      return <PriceWatch snapshot={snapshot} />;
    case "attribution":
      return <Attribution snapshot={snapshot} />;
    case "ledger":
      return <Ledger snapshot={snapshot} />;
    case "onboarding":
      return <Onboarding snapshot={snapshot} />;
    case "cost":
      return <Cost snapshot={snapshot} />;
    default:
      return <Chairs snapshot={snapshot} />;
  }
}

export function App() {
  const route = useHashRoute();
  const snapshot = useSnapshot();
  const searchRef = useRef<HTMLInputElement>(null);
  const focusSearch = useCallback(() => searchRef.current?.focus(), []);
  useKeyboardChords(focusSearch);

  return (
    <div className="floor">
      <Rail route={route} snapshot={snapshot} searchRef={searchRef} />
      <main className="page" id="main">
        <Page route={route} snapshot={snapshot} />
      </main>
    </div>
  );
}
