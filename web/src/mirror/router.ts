import { useEffect, useState } from "react";

export const routes = [
  "welcome",
  "capture",
  "card",
  "simulate",
  "price",
  "consent",
  "plan",
  "return",
] as const;

export type Route = (typeof routes)[number];

export const routeLabels: Record<Route, string> = {
  welcome: "Welcome",
  capture: "Scan",
  card: "Card",
  simulate: "Simulate",
  price: "Price",
  consent: "Consent",
  plan: "Plan",
  return: "Return",
};

export function currentRoute(): Route {
  const hash = window.location.hash.replace(/^#\/?/, "");
  return (routes as readonly string[]).includes(hash) ? (hash as Route) : "welcome";
}

export function navigate(route: Route): void {
  window.location.hash = `#/${route}`;
}

export function nextRoute(route: Route): Route | null {
  const index = routes.indexOf(route);
  return index >= 0 && index < routes.length - 1 ? routes[index + 1] : null;
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(currentRoute);
  useEffect(() => {
    const onChange = () => setRoute(currentRoute());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
