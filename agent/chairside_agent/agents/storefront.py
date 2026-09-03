"""One static page from salon data. No JS; the only interaction is the Book link into Mirror."""

from __future__ import annotations

from html import escape
from typing import Any

from chairside_agent.core.models import ShadeEntry, Sku

MAX_BYTES = 50 * 1024

STYLE = (
    "html{background:#F5F1EA;color:#161412;font:17.5px/1.45 Georgia,serif;margin:0}"
    "body{margin:0;padding:40px 24px;max-width:720px;margin-inline:auto}"
    "h1{font-size:43px;line-height:1.05;font-weight:400;margin:0 0 8px}"
    "h2{font-size:22px;font-weight:400;margin:40px 0 12px;border-top:1px solid #D8CFC2;"
    "padding-top:24px}"
    "p{margin:0 0 12px}ul{list-style:none;padding:0;margin:0}"
    "li{padding:8px 0;border-bottom:1px solid #D8CFC2}"
    ".look{display:inline-block;width:20px;height:20px;border-radius:4px;vertical-align:middle;margin-right:8px}"
    "a.book{display:inline-block;margin-top:24px;padding:12px 24px;background:#5A1F1F;"
    "color:#F5F1EA;"
    "text-decoration:none;border-radius:4px}"
    "a.book:focus{outline:3px solid #161412;outline-offset:2px}"
    "small{color:#4A443E}"
)


def _euros(cents: int) -> str:
    return f"€{cents // 100},{cents % 100:02d}"


def _service_items(skus: list[Sku]) -> str:
    services = [s for s in skus if s.kind == "service"]
    return "".join(
        f"<li>{escape(s.name)} <small>{_euros(s.salon_price_cents)}</small></li>" for s in services
    )


def _look_items(shades: list[ShadeEntry]) -> str:
    return "".join(
        f'<li><span class="look" style="background:{escape(s.hex)}"></span>'
        f"{escape(s.code)} {escape(s.name)}</li>"
        for s in shades[:3]
    )


def render_storefront(
    salon: dict[str, Any], domain: str, skus: list[Sku], looks: list[ShadeEntry]
) -> str:
    name = escape(salon["name"])
    address = escape(f"{salon['address']}, {salon['postcode']} {salon['city']}")
    html = (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{name}</title><style>{STYLE}</style></head><body>"
        f"<h1>{name}</h1><p>{address}</p>"
        f"<p><small>Sit. Scan. See.</small></p>"
        f"<h2>Services</h2><ul>{_service_items(skus)}</ul>"
        f"<h2>Three looks</h2><ul>{_look_items(looks)}</ul>"
        f'<a class="book" href="https://{escape(domain)}/mirror/">Book</a>'
        "</body></html>"
    )
    if len(html.encode("utf-8")) > MAX_BYTES:
        raise ValueError("storefront exceeds 50 KB")
    return html
