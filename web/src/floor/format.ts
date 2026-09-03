const CENTS_PER_EURO = 100;
const HASH_PREVIEW_LENGTH = 8;

const euro = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const parisTime = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Europe/Paris" });
const parisDate = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", year: "numeric", timeZone: "Europe/Paris" });
const parisClock = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Paris" });

export function formatCents(cents: number): string {
  return euro.format(cents / CENTS_PER_EURO);
}

export function formatTime(iso: string): string {
  return parisTime.format(new Date(iso));
}

export function formatClock(iso: string): string {
  return parisClock.format(new Date(iso));
}

export function formatDate(iso: string): string {
  return parisDate.format(new Date(iso));
}

export function shortHash(hash: string): string {
  return `${hash.slice(0, HASH_PREVIEW_LENGTH)}…`;
}

export function formatPercent(value: number): string {
  return `${value > 0 ? "+" : ""}${value} %`;
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)} %`;
}
