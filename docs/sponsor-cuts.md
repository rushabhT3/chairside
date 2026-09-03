# Sponsor cuts (60–90 s each, demo-first)

Each cut opens on the sponsor's own moment, shows the trace with the call count, and ends on the ledger row for that API. All seven are exported from the master timeline in `docs/video-script.md`; timestamps below refer to the master video and are the ones to link from the README's "Judges: start here" section.

| File | Opening frame | Trace / call-count shot | Ends on ledger row | Length | Master timestamp |
|---|---|---|---|---|---|
| `perfectcorp.mp4` | Mirror Capture: the oval guide, one selfie, progress names appearing (Color tones · Skin · Hair · Face shape). | Floor trace panel filtered to `mcp/beauty` and `mcp/fashion`: 4 analysis calls + 3 renders (hair color 7.31, skin simulation, hairstyle by face shape). Latency and units visible on every row. | `simulation.rendered · mcp/fashion · 7.31` | 85 s | 1:20–1:55 |
| `serpapi.mp4` | Phone camera on the Olaplex No.3 bottle; Lens result appears. | Trace filtered to `rest/serpapi`: `google_lens 1 · google_shopping 1 · google_news 1 · google_maps 1 · google_maps_reviews 2`. Cut to the Shopping JSON with the min/median/max spread beside the Price screen's range bar. | `price.snapshot · rest/serpapi · match` | 80 s | 1:55–2:20 |
| `xano.mp4` | Floor → Ledger → **Verify** turns green. | Xano workspace: tables, the `commit` API group, `POST /envelopes/{id}/send` returning 403 for the agent token and 200 for the owner; task logs for `price_refresh` and `envelope_poll`; MCP Builder server `chairside-mcp` with the OAuth Worker in front; the Claude Web booking arriving on Floor. | `booking.created · chairside-mcp · oauth` | 90 s | 1:16–1:20 and 2:28–2:40 |
| `nutrient.mp4` | Floor → Catalog: the price-list PDF drops in, 42 rows appear with confidence chips. | Trace filtered to `rest/nutrient`: `extract ×3` (price list, two invoices) + `sign cades b-lt ×1`. Viewer with bounding boxes on the two flagged rows; Confirm, Confirm. | `catalog.sealed · rest/nutrient · cades b-lt` | 75 s | 1:00–1:20 |
| `foxit.mp4` | Terminal: `chairside_agent redteam esign` → `401`. | Trace filtered to `mcp/foxit`: `merge · compress · ocr · convert` (4 tools per onboarding). Then the Commit Service gate: 403 for the agent token, 200 for the owner; the embedded signing session on the owner's phone. | `redteam.esign_denied · 401` followed by `envelope.signed · owner` | 90 s | 0:45–1:00 |
| `doctavian.mp4` | Doctavian editor: the consent template with its branching expressions on screen. | Onboarding log: `generate ×6` (consent family, aftercare, price list, client terms). Chair: `generate ×1` with the plan's treatment classes and the allergen list from the intake feeding the loop. | `consent.generated · rest/doctavian` | 70 s | 0:35–0:45 and 2:20–2:28 |
| `namecom.mp4` | Terminal: the prompt typed; `domains:search` suggestions scrolling. | Six calls in order: `search · checkAvailability · create (idempotency key visible) · dnsRecords ×2 · urlForwarding · emailForwarding`. Cut to the name.com DNS records page, then the storefront resolved on the salon's domain. | `storefront.deployed · rest/namecom` | 80 s | 0:00–0:28 |

## Cut rules

- First frame is the demo, never a title card. The sponsor's logo may appear in the last 2 s only.
- The trace shot stays on screen long enough to count the rows (≥ 3 s).
- Every cut ends on the ledger row so the judge sees the API name, the server, and the hash in one frame.
- Voice-over lines are lifted from the master script; no new claims in a cut.
- Upload each cut unlisted to the same YouTube channel as the master; link them from the README section for that sponsor.
