const salonTimeZone = "Europe/Paris";

const euroNumber = new Intl.NumberFormat("fr-FR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const timeFormat = new Intl.DateTimeFormat("fr-FR", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: salonTimeZone,
});

const dateFormat = new Intl.DateTimeFormat("fr-FR", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: salonTimeZone,
});

export function formatCents(cents: number): string {
  return `€${euroNumber.format(cents / 100)}`;
}

export function formatTime(iso: string): string {
  return timeFormat.format(new Date(iso));
}

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}

export function shortHash(hash: string | null, length = 4): string {
  return hash ? `${hash.slice(0, length)}…` : "—";
}

export function addWeeks(iso: string, weeks: number): string {
  const date = new Date(iso);
  date.setUTCDate(date.getUTCDate() + weeks * 7);
  return date.toISOString();
}
