# Screenshots checklist

## Captured on 3 Sep 2026 (fixtures mode, production build, headless Chrome)

Mirror at 500 px wide (Chrome's minimum window width on Windows; the layout column is 480 px), Floor and Storefront at 1440 × 900:
`mirror-welcome.png`, `mirror-card.png`, `mirror-simulate.png`, `mirror-price.png`, `mirror-consent.png`, `mirror-plan.png`, `mirror-return.png`, `floor-chairs.png`, `floor-consultation-trace.png`, `floor-quarantine.png`, `floor-catalog.png`, `floor-price-watch.png`, `floor-attribution.png`, `floor-ledger.png`, `floor-onboarding.png`, `floor-cost.png`, `storefront.png`, and `hero.png` (currently the Floor consultation; replace with the phone-beside-desktop composite once filmed).

Still to capture from the vendor consoles once live keys exist: everything in the table below that is not listed above.

## Full list

Every README sponsor section links one of these. Capture at 2× device pixel ratio; Floor at 1440 wide, Mirror at 390 wide in a phone frame. PNG, no compression artefacts, no personal data beyond the seeded synthetic clients.

| File | What it must show | Used by |
|---|---|---|
| `youcam-mcp-trace.png` | Floor trace panel filtered to `mcp/beauty` + `mcp/fashion`: 4 analysis rows and 3 render rows with tool name, latency, units, result hash. | Perfect Corp |
| `serpapi-shopping-spread.png` | Raw `google_shopping` JSON beside the Mirror Price screen range bar (min / median / max, "as of" time). | SerpApi |
| `serpapi-lens.png` | `google_lens` result for the Olaplex No.3 bottle with `visual_matches[].price`. | SerpApi |
| `xano-schema.png` | Xano workspace table list (all §8.1 tables visible). | Xano |
| `xano-commit-gate.png` | `POST /commit/envelopes/{id}/send` returning 403 `agent_token_rejected` and 200 with `session_url`. | Xano, Foxit |
| `xano-task-logs.png` | Background task run history for `price_refresh` and `envelope_poll`. | Xano |
| `xano-mcp-builder.png` | `chairside-mcp` server with `book_appointment`, `get_consultation_summary`, `price_check`; the OAuth Worker URL. | Xano |
| `nutrient-viewer.png` | DWS Viewer with bounding boxes drawn from extraction citations and a confidence chip per field on a flagged row. | Nutrient |
| `nutrient-seal.png` | The `sign` response (`cades`, `b-lt`) and the `catalog.sealed` ledger row with the hash. | Nutrient |
| `foxit-envelope.png` | The completed envelope in the Foxit dashboard (signed by the owner). | Foxit |
| `foxit-401-ledger.png` | Floor Ledger with the red hairline row `redteam.esign_denied` and the 401 in the payload. | Foxit |
| `foxit-mcp-tools.png` | `tools/list` from the Foxit MCP server with merge, compress, OCR, convert highlighted. | Foxit |
| `doctavian-editor.png` | Doctavian editor showing the consent template's branching (treatment class), loop (allergens) and switch (jurisdiction) expressions. | Doctavian |
| `doctavian-output.png` | A generated consent PDF for a chemical + heat plan with two allergens, FR jurisdiction. | Doctavian |
| `namecom-dns.png` | name.com DNS records for the salon domain (A, CNAME `www`) and the URL / email forwarding entries. | name.com |
| `namecom-search.png` | Terminal trace of `domains:search` → `checkAvailability` → create with the idempotency key visible. | name.com |
| `mirror-card.png` | Mirror Card: undertone swatch with hex, ranked concerns with bars, hair, face shape, the paragraph. | Perfect Corp, hero |
| `mirror-simulate.png` | Mirror Simulate: shade chips, before/after slider mid-drag, footer "Rendered 14:32 · 7.31 · this device only". | Perfect Corp |
| `mirror-price.png` | Mirror Price: product row with range bar, salon price, Match, recall line. | SerpApi |
| `mirror-consent.png` | Mirror Consent: signing sheet up with the embedded Foxit session; after-state "Sealed · hash … · Verify". | Foxit, Nutrient |
| `floor-consultation.png` | Floor Consultation: client card · trace timeline · plan editor with the staff-only competitor note. | All |
| `floor-ledger-verify.png` | Floor Ledger with Verify green and the chain length. | Xano, Nutrient |
| `floor-onboarding.png` | Floor Onboarding log: domain ✓ DNS ✓ site ✓ templates ✓ catalog 42 SKUs (3 to review) ✓ prices ✓. | name.com, Doctavian, Nutrient |
| `hero.png` | The README hero: Mirror Card on a phone beside Floor Consultation on desktop. | README top |
