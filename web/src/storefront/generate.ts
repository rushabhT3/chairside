import type { Salon } from "../lib/snapshot";

export interface StorefrontLook {
  label: string;
  image_url: string;
}

export interface StorefrontService {
  name: string;
  price_cents: number;
}

const PALETTE = {
  paper: "#F5F1EA",
  bone: "#E9E2D6",
  ink: "#161412",
  ink2: "#4A443E",
  rule: "#D8CFC2",
  accent: "#5A1F1F",
};

const CENTS_PER_EURO = 100;

function escapeHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function euro(cents: number): string {
  return `${(cents / CENTS_PER_EURO).toFixed(2).replace(".", ",")} €`;
}

const CSS = `
:root{--paper:${PALETTE.paper};--bone:${PALETTE.bone};--ink:${PALETTE.ink};--ink-2:${PALETTE.ink2};--rule:${PALETTE.rule};--accent:${PALETTE.accent}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:17.5px/1.45 Georgia,"Times New Roman",serif}
main{max-width:920px;margin:0 auto;padding:64px 24px 96px}
header{padding-bottom:24px;border-bottom:1px solid var(--rule)}
h1{font-size:43px;line-height:1.05;font-weight:400;margin:0 0 8px}
h2{font-size:27px;line-height:1.05;font-weight:400;margin:64px 0 16px}
p{margin:0}
.address{color:var(--ink-2)}
.tag{font-size:22px;margin-top:24px}
.cta{display:inline-block;margin-top:24px;padding:12px 24px;border:1px solid var(--ink);border-radius:4px;background:var(--ink);color:var(--paper);text-decoration:none;font-size:17.5px;min-height:44px}
.cta:hover,.cta:focus{background:var(--accent);outline:2px solid var(--accent);outline-offset:2px}
.looks{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:0;padding:0;list-style:none}
.looks img{width:100%;height:auto;border:1px solid var(--rule);display:block}
.looks figcaption{margin-top:8px;font-size:14px;color:var(--ink-2)}
figure{margin:0}
table{width:100%;border-collapse:collapse;font-size:17.5px}
td{padding:12px 0;border-bottom:1px solid var(--rule)}
td:last-child{text-align:right;font-variant-numeric:tabular-nums}
footer{margin-top:64px;padding-top:16px;border-top:1px solid var(--rule);font-size:14px;color:var(--ink-2)}
@media (max-width:768px){.looks{grid-template-columns:1fr}h1{font-size:34px}main{padding:40px 16px 64px}}
`.trim();

export function generateStorefront(salon: Salon, looks: StorefrontLook[], mirrorUrl: string, services: StorefrontService[] = []): string {
  const name = escapeHtml(salon.name);
  const address = escapeHtml(`${salon.address}, ${salon.postcode} ${salon.city}`);
  const looksHtml = looks
    .map(
      (look) =>
        `<li><figure><img src="${escapeHtml(look.image_url)}" alt="${escapeHtml(look.label)}" width="400" height="520" loading="lazy"><figcaption>${escapeHtml(look.label)}</figcaption></figure></li>`,
    )
    .join("");
  const servicesHtml = services.map((s) => `<tr><td>${escapeHtml(s.name)}</td><td>${euro(s.price_cents)}</td></tr>`).join("");
  return `<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="${name} — ${address}. Sit. Scan. See.">
<title>${name}</title>
<style>${CSS}</style>
</head>
<body>
<main>
<header>
<h1>${name}</h1>
<p class="address">${address}</p>
<p class="tag">Sit. Scan. See.</p>
<a class="cta" href="${escapeHtml(mirrorUrl)}">Book a consultation</a>
</header>
<h2>Three looks from this chair</h2>
<ul class="looks">${looksHtml}</ul>
<h2>Services</h2>
<table><tbody>${servicesHtml}</tbody></table>
<footer><p>${name} · ${escapeHtml(salon.domain)} · consultations run on Chairside; your selfie is processed and deleted after rendering unless you keep it.</p></footer>
</main>
</body>
</html>
`;
}
