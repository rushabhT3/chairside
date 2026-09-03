# Chairside shared contracts

Every package (agent, xano, web, worker-oauth) builds against this file. Change it here first.

## 1. Modes and cassettes
- `CHAIRSIDE_MODE=fixtures` (default) replays cassettes from `agent/chairside_agent/fixtures/<vendor>/<primitive>[.<variant>].json`.
- `CHAIRSIDE_MODE=live` calls the vendor. With `RECORD=1` it also writes the cassette.
- Cassette JSON: `{"vendor","primitive","variant","recorded_at","request":{...},"response":{...},"units":<int>,"latency_ms":<int>}`.
  `response` is the vendor's JSON verbatim (binary bodies as base64 under `"_base64"`). `FIXTURE`-labelled PDFs live in `seed/`.
- Loader: `chairside_agent.fixtures.load(vendor, primitive, variant="default") -> Cassette`.
- Base adapter: `chairside_agent.adapters.base.VendorAdapter.call(primitive, variant, live_fn)` picks the path and emits a `tool.called` event.

## 2. Event model (`chairside_agent.events`)
`ConsultationEvent{id: str, consultation_id: str | None, salon_id: str, type: EventType, payload: dict, ts: str (ISO-8601 UTC, ms), actor: "agent" | "owner" | "stylist" | "client" | "system"}`.
`tool.called` payload is exactly `{tool, server, latency_ms, units, result_sha256, as_of}`; `server` is one of `mcp/beauty`, `mcp/fashion`, `mcp/foxit`, `rest/serpapi`, `rest/namecom`, `rest/doctavian`, `rest/nutrient`, `rest/xano`, `commit/xano`.
Event types (strings; the enum is in `events.py` and must stay in sync with `web/src/lib/events.ts`):
```
capture.uploaded color_tones.done skin_hd.done hair_diagnostics.done face_attributes.done
plan.recommended simulation.rendered price.identified price.snapshot news.checked reviews.fetched
consent.template_selected consent.generated intake.extracted envelope.requested envelope.sent envelope.signed
bundle.sealed plan.accepted order.created booking.created state.changed needs_attention quarantined
redteam.esign_denied data.tombstoned tool.called
onboarding.parsed domain.searched domain.available domain.created dns.created forwarding.created
documents.generated agreement.requested agreement.signed catalog.extracted catalog.review_queued
catalog.sealed prices.seeded shade_map.seeded storefront.deployed onboarding.done
```
Every event that describes something external carries `as_of` (ISO-8601) in its payload.

## 3. Audit chain
`audit_event{id, prev_hash, hash, actor, action, payload_hash, ts}`.
- `canonical(obj)` = JSON, keys sorted recursively, separators `,` and `:`, no whitespace, UTF-8, non-ASCII unescaped. **No floats anywhere in audited payloads**: money is integer cents (`price_cents`), scores are integers 0-100.
- `payload_hash = sha256_hex(canonical(payload))`
- `hash = sha256_hex(canonical({"action","actor","payload_hash","prev_hash","ts"}))` (keys sorted).
- Genesis `prev_hash` is 64 zero characters. Verify = recompute every hash and check each `prev_hash` equals the previous row's `hash`.
- Python: `chairside_agent.hashing`. TypeScript: `web/src/lib/hashchain.ts`. Both are unit-tested against the same vectors in `docs/hash-vectors.json`.

## 4. Domain models (`chairside_agent.core.models`)
- `ColorTones{skin_tone: str, undertone: "warm"|"cool"|"neutral", eye_color: str, hair_color_hex: str}`
- `SkinScores{scores: dict[str, int]}` with keys `wrinkle, spot, pore, texture, acne, redness, oiliness, dark_circle, eye_bag, droopy_upper_eyelid, droopy_lower_eyelid, firmness, radiance, moisture` (0-100, higher = more concern; `radiance`, `moisture`, `firmness` are inverted: higher = better).
- `HairDiagnostics{type: "straight"|"wavy"|"curly"|"coily", frizz: int, density: "low"|"medium"|"high"}`
- `FaceAttributes{shape: "oval"|"round"|"square"|"heart"|"oblong"|"diamond", ratios: dict[str,int]}`
- `Sku{code, name, brand, salon_price_cents, shade_code: str|None, kind: "retail"|"backbar"|"service"}`
- `ShadeEntry{line, code, name, hex, undertone, level: int}`
- `Plan{treatment_classes: list["chemical"|"heat"|"injectable"|"laser"|"none"], services: list[PlanItem], products: list[PlanItem], total_cents: int, rebook_weeks: int, facts: list[str]}`; `PlanItem{code, name, price_cents, qty, treatment_class}`
- `PriceSnapshot{sku_code, min_cents, median_cents, max_cents, as_of, source: "google_shopping"}`
- `PriceVerdict{action: "match"|"bundle"|"hold", reason: str}`
- `ConsentSelection{template_id: str, variables: dict}` with variables `treatment_classes, allergens, jurisdiction ("FR"|"US"), salon{name,address}, client{name}`.
- `Extraction{source: "price_list"|"invoice"|"intake", fields: list[Field], text: str}`; `Field{name, value, confidence: float, page: int, bbox: [x,y,w,h]}` (confidence is the one float; it never enters an audit payload).
- `QuarantineVerdict{quarantined: bool, reasons: list[str]}`

## 5. Xano REST contract (base = `XANO_BASE_URL`)
Auth: `Authorization: Bearer <jwt>`. JWT claims: `sub`, `role` in owner|stylist|client|agent, `salon_id`.

Group `auth`: `POST /auth/signup {email,password,name,role}` · `POST /auth/login {email,password} -> {authToken}` · `GET /auth/me`.

Group `mirror`: `POST /mirror/scans {consultation_id} -> {scan_id, upload_url}` · `POST /mirror/scans/{id}/complete {image_sha256, retained}` · `GET /mirror/consultations/{id}` · `POST /mirror/consultations/{id}/accept-plan` · `POST /mirror/clients/{id}/retention {retained}` · `DELETE /mirror/clients/{id}/data`.

Group `floor`: `GET /floor/chairs` · `GET /floor/consultations/{id}` (includes `events[]`) · `PATCH /floor/plans/{id}` · `GET|POST|PATCH /floor/skus` · `GET|POST|PATCH /floor/shade_map` · `GET /floor/extractions?needs_review=true` · `POST /floor/extractions/{id}/confirm {fields}` · `GET /floor/attribution` · `GET /floor/ledger` · `GET /floor/ledger/verify` · `GET /floor/price_watch` · `GET /floor/onboarding/{salon_id}` · `GET /floor/cost`.

Group `agent`: `POST /agent/events {events:[ConsultationEvent]}` (appends events + one audit_event per event) · `PATCH /agent/consultations/{id}/state {state, failing_step?}` · `POST /agent/skus` · `POST /agent/documents {kind,url,sealed_hash}` · `POST /agent/envelopes {consultation_id?, document_id, signer{name,email}} -> {envelope_id, state:"draft"}` · `POST /agent/consultations {client_id, chair, stylist} -> {id}` · `POST /agent/orders {consultation_id, items, total_cents} -> {id}` · `POST /agent/bookings {consultation_id, when, service} -> {id}`.

Group `commit`: `POST /commit/envelopes/{id}/send` (the gate) · `GET /commit/envelopes/{id}/status` · `POST /commit/envelopes/{id}/reissue-session`.

Gate responses: 403 `{reason:"role_not_allowed"|"agent_token_rejected"|"state_not_human_reviewed"|"consent_not_ready"|"docs_not_reviewed"}`; 200 `{session_url, expires_at, provider_id}`.

Consultation states: `capture color_tones skin_hd hair_diagnostics face_attributes plan simulations price consent commit done needs_attention`.
Envelope states: `draft human_reviewed sent signed expired`.

## 6. Seed shapes (`seed/`)
- `salon.json {id,name,address,city,postcode,country:"FR",jurisdiction:"FR",owner{name,email},stylists[{name,email}],chairs:3,color_line:"Majirel"}`
- `shade_map.json [ShadeEntry]` · `skus.json [Sku]` · `clients.json [{id,name,email,visits:[{scan_id, ts, color_tones, skin, hair, face}]}]`
- `doctavian_templates.json {consent:{chemical,heat,injectable,laser,combined}, aftercare, price_list, client_terms}` mapping to template ids (FIXTURE ids until credentials arrive).
- `invoices/*.pdf` (3; `inv-0003-bad-math.pdf` has the arithmetic error) · `intake/*.png` (3; `intake-03-adversarial.png` carries the injection).

## 7. Deterministic core signatures (`chairside_agent.core`)
```
recommend_plan(skin: SkinScores, hair: HairDiagnostics, face: FaceAttributes, catalog: list[Sku]) -> Plan
price_policy(salon_price_cents: int, snapshot: PriceSnapshot) -> PriceVerdict
consent_template_select(plan: Plan, allergens: list[str], jurisdiction: str, salon: dict, client: dict, templates: dict) -> ConsentSelection
sku_shade_map(shade_code: str, shade_map: list[ShadeEntry]) -> ShadeEntry   # raises UnknownShadeError
quarantine_policy(extraction: Extraction, *, known_invoice_numbers: set[tuple[str,str]] = frozenset(), face_count: int = 1, plan: Plan|None = None, consented_classes: set[str] = frozenset()) -> QuarantineVerdict
```

## 8. Adapter method signatures (`chairside_agent.adapters.*`)
All adapters subclass `VendorAdapter` and route every vendor call through `self.call(primitive, request, live, variant=..., units=..., tool=..., server=...)`. Every primitive ships a cassette under `fixtures/<vendor>/`. Bytes travel as base64 strings inside cassettes under `"_base64"`.

```
youcam.YouCamAdapter            server mcp/beauty for every tool (Perfect Corp docs put all hair tools on Beauty; Fashion is apparel and is only listed via tools/list)
  list_tools() -> list[str]
  color_tones(image_url) -> ColorTones
  skin_hd(image_url) -> SkinScores
  hair_diagnostics(image_url) -> HairDiagnostics
  face_attributes(image_url) -> FaceAttributes
  hair_color_tryon(image_url, hex) -> RenderResult{image_url, tool, server, as_of}
  hairstyle_tryon(image_url, style_id) -> RenderResult
  bangs_tryon(image_url, bangs_id) -> RenderResult
  hair_volume_tryon(image_url, level) -> RenderResult
  skin_simulation(image_url, treatment) -> RenderResult
  aging_simulation(image_url, years) -> RenderResult

serpapi.SerpApiAdapter          server rest/serpapi
  lens(image_url) -> LensResult{brand, product, visual_matches:[{title, price_cents, currency, in_stock, source, link}], as_of}
  shopping(query, sku_code) -> ShoppingResult{snapshot: PriceSnapshot, offers:[{title, price_cents, source, link}]}
  news(query, days=90) -> NewsResult{flags:[{title, source, date, link}], clean: bool, as_of}
  maps_nearby(ll, query="hair salon", limit=2) -> list[Competitor{place_id, name, rating, address}]
  maps_reviews(place_id, topic) -> ReviewSummary{place_id, summary, quotes: list[str], as_of}

namecom.NameComAdapter          server rest/namecom
  search(keyword) -> list[DomainSuggestion{domain_name, purchasable, purchase_price_cents}]
  check_availability(names) -> list[DomainAvailability{domain_name, purchasable, premium, purchase_price_cents}]
  create_domain(domain_name, idempotency_key) -> DomainRecord{domain_name, expire_date, order_id}
  create_dns_record(domain_name, host, type, answer, ttl=300) -> DnsRecord{id, host, type, answer, ttl}
  create_url_forwarding(domain_name, host, forwards_to) -> Forwarding{domain_name, host, forwards_to}
  create_email_forwarding(domain_name, alias, forwards_to) -> EmailForwarding{domain_name, alias, forwards_to}

nutrient.NutrientAdapter        server rest/nutrient
  extract(document: bytes, schema_name: "price_list"|"invoice"|"intake", filename) -> Extraction
  build(parts: list[bytes], *, ocr=False, pdfa=False) -> bytes
  sign_cades(pdf: bytes) -> SealResult{pdf: bytes, sha256}

foxit_pdf.FoxitPdfAdapter       server mcp/foxit  (stdio MCP; tool names discovered from tools/list)
  list_tools() -> list[str]
  merge(pdfs: list[bytes]) -> bytes
  compress(pdf: bytes) -> bytes
  ocr(document: bytes) -> OcrResult{text, pdf: bytes}
  convert_to_pdf(document: bytes, filename) -> bytes

foxit_esign_proxy.EsignProxy    server commit/xano   (agent token only; NO eSign credentials)
  request_envelope(document_id, signer{name,email}, consultation_id=None) -> {envelope_id, state}
  status(envelope_id) -> {state, session_url|None, expires_at|None}
  redteam_direct_esign_call() -> int   (HTTP status from a direct eSign call using the PDF Services token; expected 401)

doctavian.DoctavianAdapter      server rest/doctavian
  generate(template_id, data) -> GeneratedDocument{document_id, pdf: bytes, url, as_of}
  clickwrap(template_id, data) -> Clickwrap{url, acceptance_id, as_of}

xano.XanoAdapter                server rest/xano  (also implements EventSink)
  append(events) -> list[AuditEvent]
  set_state(consultation_id, state, failing_step=None)
  upsert_skus(skus) ; put_shade_map(entries) ; create_document(kind, url, sealed_hash) -> str
  create_consultation(client_id, chair, stylist) -> str ; create_order(consultation_id, items, total_cents) -> str
  create_booking(consultation_id, when, service) -> str ; get_ledger() -> list[dict] ; verify_ledger() -> dict
```
In fixtures mode `XanoAdapter` delegates to `LocalLedger` and an in-memory store; the agent never needs network.

## 9. Web snapshot (judge mode data source)
`web/src/fixtures/snapshot.json` is what Mirror and Floor render when `VITE_DATA_MODE=fixtures` (default). `scripts/export_snapshot.py` regenerates it from the local ledger. Types in `web/src/lib/snapshot.ts`.
