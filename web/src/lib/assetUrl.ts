const ABSOLUTE_SCHEME = /^[a-z][a-z0-9+.-]*:/i;

function stripLeadingSlash(path: string): string {
  return path.startsWith("/") ? path.slice(1) : path;
}

export function siteRoot(pageHref: string): URL {
  return new URL("../", pageHref);
}

export function assetUrl(path: string, pageHref: string = window.location.href): string {
  if (ABSOLUTE_SCHEME.test(path)) return path;
  return new URL(stripLeadingSlash(path), siteRoot(pageHref)).href;
}

export function siteRelativeHref(path: string): string {
  if (ABSOLUTE_SCHEME.test(path)) return path;
  return `../${stripLeadingSlash(path)}`;
}
