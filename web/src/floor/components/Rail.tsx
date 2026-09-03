import { useMemo, useState, type KeyboardEvent, type RefObject } from "react";
import { href, navigate, type PageName, type Route } from "../router";
import type { SnapshotState } from "../useSnapshot";

export interface RailProps {
  route: Route;
  snapshot: SnapshotState;
  searchRef: RefObject<HTMLInputElement | null>;
}

const LINKS: { page: PageName; label: string; key: string }[] = [
  { page: "chairs", label: "Chairs", key: "g c" },
  { page: "catalog", label: "Catalog", key: "g k" },
  { page: "price-watch", label: "Price watch", key: "g p" },
  { page: "attribution", label: "Attribution", key: "g a" },
  { page: "ledger", label: "Ledger", key: "g l" },
  { page: "onboarding", label: "Onboarding", key: "g o" },
  { page: "cost", label: "Cost", key: "g $" },
];

const MAX_RESULTS = 6;

function isCurrent(route: Route, page: PageName): boolean {
  if (page === "catalog") return route.page === "catalog" || route.page === "catalog-review";
  if (page === "chairs") return route.page === "chairs" || route.page === "consultation";
  return route.page === page;
}

export function Rail({ route, snapshot, searchRef }: RailProps) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);

  const results = useMemo(() => {
    if (snapshot.status !== "ready" || query.trim() === "") return [];
    const needle = query.trim().toLowerCase();
    return Object.values(snapshot.data.consultations)
      .filter((c) => c.client.name.toLowerCase().includes(needle) || c.id.includes(needle))
      .slice(0, MAX_RESULTS);
  }, [query, snapshot]);

  const open = (id: string) => {
    setQuery("");
    setSelected(0);
    navigate({ page: "consultation", id });
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setSelected((s) => Math.min(s + 1, Math.max(results.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (event.key === "Enter" && results[selected]) {
      open(results[selected].id);
    } else if (event.key === "Escape") {
      setQuery("");
      event.currentTarget.blur();
    }
  };

  const salonName = snapshot.status === "ready" ? snapshot.data.salon.name : "";

  return (
    <nav className="rail" aria-label="Floor">
      <div className="rail__brand">
        Floor
        <span className="rail__salon">{salonName || "Chairside"}</span>
      </div>
      <div className="rail__search">
        <label className="visually-hidden" htmlFor="floor-search">
          Search clients and consultations
        </label>
        <input
          ref={searchRef}
          id="floor-search"
          className="rail__input"
          type="search"
          placeholder="Search clients · /"
          autoComplete="off"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelected(0);
          }}
          onKeyDown={onKeyDown}
          role="combobox"
          aria-expanded={results.length > 0}
          aria-controls="floor-search-results"
          aria-autocomplete="list"
        />
        {results.length > 0 && (
          <ul className="rail__results" id="floor-search-results" role="listbox">
            {results.map((c, i) => (
              <li key={c.id} role="none">
                <button
                  type="button"
                  className="rail__result"
                  role="option"
                  aria-selected={i === selected}
                  onMouseEnter={() => setSelected(i)}
                  onClick={() => open(c.id)}
                >
                  <span>{c.client.name}</span>
                  <span className="mono">{c.id}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="rail__nav">
        {LINKS.map((link) => (
          <a
            key={link.page}
            className="rail__link"
            href={href({ page: link.page } as Route)}
            aria-current={isCurrent(route, link.page) ? "page" : undefined}
          >
            <span>{link.label}</span>
            <span className="rail__key" aria-hidden="true">
              {link.key}
            </span>
          </a>
        ))}
      </div>
      <p className="rail__foot">
        <kbd>/</kbd> search · <kbd>g</kbd> then a letter to jump · arrows move in tables
      </p>
    </nav>
  );
}
