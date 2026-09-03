# Chairside — master video script (3:00)

Format: 1920×1080, 30 fps. Every external call appears as a trace overlay (bottom-right, monospace, `tool · server · latency · units · hash`) pulled from the Floor trace panel. Fixtures mode for every retake; live only for the first take of each vendor moment.

Voice-over is read flat and quiet. No music under the terminal shots; a single room tone under Mirror shots.

## Shot list

| Time | On screen | Overlay / trace | Voice-over |
|---|---|---|---|
| 0:00–0:04 | Black. The prompt is typed into a terminal, one line, no cursor blink effects. | — | "One prompt opens a salon." |
| 0:04–0:10 | Terminal runs `chairside_agent open …`. Lines appear: `parse_prompt ✓ Atelier Noor · 3 chairs · FR`. | `domains:search · rest/namecom` → `domains:checkAvailability · rest/namecom` → `domains create · X-Idempotency-Key: 6f1c…` | "The agent looks for a name, checks it, and registers it. The idempotency key means a retry cannot buy it twice." |
| 0:10–0:18 | Terminal: DNS records created, A and CNAME for apex and `www`, URL forwarding, email forwarding for `hello@`. | `dnsRecords create ×2` · `urlForwarding create` · `emailForwarding create` (6 name.com calls total) | "DNS points at Xano static hosting. `www` forwards to the apex. `hello@` forwards to the owner." |
| 0:18–0:28 | Cut to browser: Storefront resolved on the salon's own domain. Scroll once. | `storefront.deployed` ledger row | "Minutes later the storefront is live on the salon's domain." |
| 0:28–0:35 | Tap **Book**. Mirror opens on a phone frame. Welcome screen. | — | "Book opens Mirror." |
| 0:35–0:45 | Floor → Onboarding log. Doctavian template family generated; the consent template shows branching expressions as treatment classes are added (chemical, heat). | `generate · rest/doctavian ×6` | "Doctavian generates the salon's paper: consent that branches by treatment, loops over allergens, switches by jurisdiction." |
| 0:45–0:52 | Terminal: Foxit MCP merges aftercare + consent + terms into one packet; compress. | `merge · mcp/foxit` · `compress · mcp/foxit` | "Foxit's MCP server does the reversible work." |
| 0:52–0:58 | Terminal: `chairside_agent redteam esign` → `401 Unauthorized`. Cut to Floor → Ledger: red hairline row `redteam.esign_denied`. | `redteam.esign_denied · commit/xano · 401` | "The agent is forced to try the eSign API with its own token. It has none. The refusal goes in the ledger." |
| 0:58–1:00 | Phone: owner signs the platform agreement in the embedded Foxit session. | `envelope.sent` → `envelope.signed` | "Only a person signs." |
| 1:00–1:08 | Floor → Catalog. The salon's price-list PDF drops in; 42 rows appear with confidence chips; 3 flagged. | `extract · rest/nutrient ×3` | "Nutrient reads the salon's existing price list and last month's invoices into SKUs, with a confidence per field." |
| 1:08–1:16 | Nutrient Viewer: two flagged rows, bounding boxes drawn from citations; Confirm, Confirm. | confidence `0.71 → confirmed` | "Rows under 0.85 wait for a human." |
| 1:16–1:20 | Catalog sealed; Ledger → Verify → green. | `sign cades b-lt · rest/nutrient` · `catalog.sealed` | "The confirmed catalog is sealed. Verify recomputes the chain in the browser." |
| 1:20–1:28 | Chair. Phone: Capture, oval guide, one selfie. Progress: Color tones · Skin · Hair · Face shape. | `AI_Facial_Color_Tones_Analyzer · mcp/beauty` · `AI_Skin_Analysis · mcp/beauty` · hair diagnostics · `AI_Face_Attributes · mcp/beauty` | "One selfie. Four YouCam analyses over MCP." |
| 1:28–1:38 | Card: undertone swatch with hex, concerns ranked, hair type, face shape, one paragraph. | `plan.recommended` (pure) | "The plan is a table, not a guess. The model only writes the paragraph." |
| 1:38–1:50 | Simulate: tap shade chip `7.31 Medium Blonde Gold Ash` → render; drag the before/after slider. Tab to Skin plan → before/after. | `hair color try-on · mcp/fashion` · `AI_Skin_simulation · mcp/beauty` | "Rendered in the salon's own shade, on the client's own face." |
| 1:50–1:55 | Style tab: hairstyle candidates chosen by face shape. | `hairstyle try-on · mcp/fashion` | "Styles picked by face shape." |
| 1:55–2:03 | Phone: camera on a bottle of Olaplex No.3. Lens identifies it. | `google_lens · rest/serpapi` | "The client photographs the bottle in their hand. Lens names it." |
| 2:03–2:12 | Price screen: market range bar (min / median / max), salon price beside it, **Match**. "as of 14:33". | `google_shopping · rest/serpapi` · `price_policy → match` | "Shopping gives the spread. The salon matches. The policy is a function." |
| 2:12–2:16 | Recall line: "No recalls or ingredient flags in the last 90 days." | `google_news · rest/serpapi` | "News over ninety days: clean." |
| 2:16–2:20 | Floor: staff-only note, what clients say about this treatment at the two nearest competitors. | `google_maps · google_maps_reviews ×2 · rest/serpapi` | "Reviews from the two nearest competitors, for staff only." |
| 2:20–2:28 | Consent: treatment classes in plain language; signing sheet slides up; client signs on their phone. "Sealed · hash 7f3a… · Verify". | `consent_template_select` · `generate · rest/doctavian` · `extract intake · rest/nutrient` · `envelope.sent · commit/xano` | "Consent picked by the plan's treatment classes, the handwritten intake read with confidence, signed by the client." |
| 2:28–2:34 | Floor: one tap **Commit**. Plan → order €147 → rebook in 6 weeks. Attribution updates for Léa, chair 2. | `order.created` · `booking.created` | "One tap. Plan, order, rebooking, attributed." |
| 2:34–2:40 | Claude Web: "Book me a gloss at Atelier Noor next Thursday." → booking lands on Floor with the user's identity. | `chairside-mcp · book_appointment` via OAuth proxy | "Other agents can book through Chairside's own MCP server." |
| 2:40–2:55 | Return: six weeks later, new scan overlaid on the last; per-concern deltas with arrows; plan adapts. | `skin_hd.done` ×2 compared | "Six weeks later, the scan overlays the last one. The plan changes with the face." |
| 2:55–3:00 | Ledger, full chain, Verify green. Title card: **Chairside remembers.** | — | "Chairside remembers." |

## Terminal commands shown on screen

```
chairside_agent open "Open Chairside for Atelier Noor, 14 Rue de Turenne, 75003 Paris. Hair, skin, brows. Three chairs. Owner: Noor Haddad, noor@example.com."
chairside_agent redteam esign
chairside_agent consult cl-01 --chair 2 --stylist Léa
chairside_agent replay <consultation_id>
```

## Recording notes

- Terminal: 110 columns, 14 pt monospace, paper background (`#F5F1EA`), ink text (`#161412`). No shell prompt decorations.
- Phone frame for Mirror at 390 px logical width; desktop for Floor at 1440.
- Film the name.com and DNS calls live once (sandbox), then cut to the resolved storefront; propagation is minutes, not seconds.
- Keep every overlay on screen for at least 1.5 s. Judges pause the video to read them.
- Export the seven sponsor cuts from this timeline (see `docs/sponsor-cuts.md`).
