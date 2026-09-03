import { useEffect, useState } from "react";

export type Route =
  | { page: "chairs" }
  | { page: "consultation"; id: string }
  | { page: "catalog" }
  | { page: "catalog-review"; id: string }
  | { page: "price-watch" }
  | { page: "attribution" }
  | { page: "ledger" }
  | { page: "onboarding" }
  | { page: "cost" };

export type PageName = Route["page"];

export function parseHash(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const [head, second, third] = parts;
  if (head === "consultation" && second) return { page: "consultation", id: second };
  if (head === "catalog" && second === "review" && third) return { page: "catalog-review", id: third };
  if (head === "catalog") return { page: "catalog" };
  if (head === "price-watch") return { page: "price-watch" };
  if (head === "attribution") return { page: "attribution" };
  if (head === "ledger") return { page: "ledger" };
  if (head === "onboarding") return { page: "onboarding" };
  if (head === "cost") return { page: "cost" };
  return { page: "chairs" };
}

export function href(route: Route): string {
  switch (route.page) {
    case "consultation":
      return `#/consultation/${route.id}`;
    case "catalog-review":
      return `#/catalog/review/${route.id}`;
    default:
      return `#/${route.page}`;
  }
}

export function navigate(route: Route): void {
  window.location.hash = href(route);
}

export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));
  useEffect(() => {
    const onHashChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  return route;
}
