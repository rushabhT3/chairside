import { useEffect } from "react";
import { navigate, type Route } from "./router";

const CHORD_TIMEOUT_MS = 900;

const CHORDS: Record<string, Route> = {
  c: { page: "chairs" },
  k: { page: "catalog" },
  p: { page: "price-watch" },
  a: { page: "attribution" },
  l: { page: "ledger" },
  o: { page: "onboarding" },
  $: { page: "cost" },
};

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
}

export function useKeyboardChords(focusSearch: () => void): void {
  useEffect(() => {
    let pendingG = false;
    let timer: number | undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (isTypingTarget(event.target)) return;
      if (event.key === "/") {
        event.preventDefault();
        focusSearch();
        return;
      }
      if (pendingG) {
        pendingG = false;
        window.clearTimeout(timer);
        const route = CHORDS[event.key];
        if (route) {
          event.preventDefault();
          navigate(route);
        }
        return;
      }
      if (event.key === "g") {
        pendingG = true;
        timer = window.setTimeout(() => {
          pendingG = false;
        }, CHORD_TIMEOUT_MS);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.clearTimeout(timer);
    };
  }, [focusSearch]);
}
