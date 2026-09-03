# Xano workspace — Chairside backend

Xano is the system of record, the auth, the nightly price engine, the signing gate, the host, and an MCP server other agents can book through. Everything here is XanoScript, pushed with `@xano/cli`.

```
xano/workspace/
├── workspace/chairside.xs        env var names (values are set in the dashboard, never pushed)
├── table/*.xs                    24 tables (brief §8.1 + user, onboarding)
├── function/
│   ├── audit/append.xs           hash chain append (docs/contracts.md §3)
│   ├── audit/verify.xs           server-side chain verification
│   ├── rbac/require_staff.xs     owner|stylist gate; agent token → agent_token_rejected
│   ├── rbac/require_agent.xs     agent-only gate for the agent group
│   ├── esign/*.xs                Foxit eSign: token, createfolder, getfolder, download, regenerate
│   ├── events/append_one.xs      consultation_event + audit_event in one call
│   ├── price/*.xs                median + delta helpers (integers only)
│   └── snapshot/*.xs             web snapshot projections (web/src/lib/snapshot.ts)
├── api/{auth,mirror,floor,agent,commit}/   api_group.xs + one file per endpoint
├── task/*.xs                     price_refresh · envelope_poll · session_reissue · return_reminder
└── ai/tool/*.xs + ai/mcp_server/chairside_mcp.xs
```

## URL mapping

Every API group has an instance-unique canonical. The contract paths in `docs/contracts.md` map like this:

| Contract prefix | Live URL |
|---|---|
| `/auth/...` | `https://<instance>.xano.io/api:chairside-auth/...` |
| `/mirror/...` | `https://<instance>.xano.io/api:chairside-mirror/...` |
| `/floor/...` | `https://<instance>.xano.io/api:chairside-floor/...` |
| `/agent/...` | `https://<instance>.xano.io/api:chairside-agent/...` |
| `/commit/...` | `https://<instance>.xano.io/api:chairside-commit/...` |

`XANO_BASE_URL` in the agent's `.env` is `https://<instance>.xano.io`; the Python `XanoAdapter` inserts the `api:chairside-<group>` segment.

## Push the workspace

```bash
npm i -g @xano/cli@1.2.0
xano auth                                   # browser login; credentials land in ~/.xano/credentials.yaml
# Workspace settings → enable "CLI push to workspace" (required on free plans; paid plans can use `xano sandbox push`)
xano workspace pull -d ./xano/workspace     # first time only, to pick up guids the backend assigns
xano workspace push -d ./xano/workspace --dry-run
xano workspace push -d ./xano/workspace
```

Rules:
- Never push with `--env`. `workspace/chairside.xs` declares the env var **names** with empty values; the secrets are set in the dashboard (Settings → Environment Variables).
- `push` is additive. Use `--sync` only when a destructive schema change is intended.
- Leave any `guid = "..."` lines the backend adds after a pull exactly as they are.

## Validate before pushing

Every `.xs` file here has been validated with the bundled validator from `@xano/developer-mcp@2.2.5` (96 files, 0 errors). To run it yourself:

```bash
claude mcp add xano -- npx -y @xano/developer-mcp@2.2.5     # inside Claude Code
# then: xano_validate_xanoscript({ directory: "xano/workspace" })
```

Or without an agent:

```bash
npm i @xano/developer-mcp@2.2.5
node -e "import('@xano/developer-mcp').then(m=>console.log(JSON.stringify(m.validateXanoscript({directory:'xano/workspace'}),null,1)))"
```

Validation is syntax-only. After the first push, run each endpoint once from the dashboard (validate → push → run).

## Environment variables (dashboard only)

| Name | Used by |
|---|---|
| `FOXIT_ESIGN_CLIENT_ID` | `function/esign/access_token.xs` |
| `FOXIT_ESIGN_CLIENT_SECRET` | `function/esign/access_token.xs` |
| `FOXIT_ESIGN_BASE_URL` | region host, e.g. `https://na1.foxitesign.foxit.com` (EU: `https://eu1.foxitesign.foxit.com`) |
| `SERPAPI_API_KEY` | `task/price_refresh.xs` |
| `AUDIT_HMAC_KEY` | reserved for signed ledger exports |

Nothing else in the repository ever holds the eSign credentials. The agent process gets `FOXIT_CLOUD_API_*` (PDF Services) only; `chairside_agent redteam esign` proves the PDF Services token is refused by eSign.

## Create the agent service token

1. Table `user` → add a record: `name = Chairside Agent`, `email = agent@chairside.local`, a strong password, `role = agent`, `salon_id = <Atelier Noor id>`.
2. `POST /api:chairside-auth/login {email, password}` → `authToken`. Put it in the agent's `.env` as `XANO_AGENT_TOKEN`.
3. Tokens issued by `login` expire after 24 h (`expiration = 86400`). The agent re-logs in with `XANO_AGENT_EMAIL` / `XANO_AGENT_PASSWORD` when it sees a 401, or you rerun step 2.

The agent role can only be assigned from the dashboard: `POST /auth/signup` accepts `owner | stylist | client`.

## Static hosting

Three sites; Mirror and Storefront share the salon domain, Floor lives on the platform domain. Keep the default Xano URL live until the custom domain resolves.

```bash
cd web && npm run build            # web/dist/{mirror,floor,storefront}
xano static_host create chairside-salon --description "Mirror + Storefront on the salon domain"
xano static_host create chairside-floor --description "Floor pro console"
xano static_host build push chairside-salon -d ./web/dist -n "v0.1.0"
xano static_host build push chairside-floor -d ./web/dist -n "v0.1.0"
xano static_host build list chairside-salon        # note the build id
xano static_host build deploy chairside-salon --build_id <id> --env prod
xano static_host build deploy chairside-floor --build_id <id> --env prod
```

Custom domain: site settings (gear icon) → Custom domain → Xano shows the DNS records to create. The Onboarding Agent creates exactly those records through name.com (`namecom.create_dns_record`) for the apex and `www`.

## Endpoint table

| Group | Endpoint | Who | Notes |
|---|---|---|---|
| auth | `POST /signup` | public | roles owner/stylist/client |
| auth | `POST /login` | public | JWT extras: `role`, `salon_id` |
| auth | `GET /me` | any | |
| mirror | `POST /scans` | client/staff | returns `scan_id` + `upload_url` (`/scans/{id}/upload`, file input) |
| mirror | `POST /scans/{id}/upload` | client/staff | private attachment; returns a 15-min signed URL for the agent |
| mirror | `POST /scans/{id}/complete` | client/staff | records on-device sha256, appends `capture.uploaded` |
| mirror | `GET /consultations/{id}` | own client / staff | never includes competitor reviews |
| mirror | `POST /consultations/{id}/accept-plan` | own client | appends `plan.accepted` |
| mirror | `POST /clients/{id}/retention` | own client | toggle; applies to existing scans |
| mirror | `DELETE /clients/{id}/data` | own client | tombstones, deletes images + scores, appends `data.tombstoned` |
| floor | `GET /chairs` · `GET /consultations/{id}` · `PATCH /plans/{id}` | staff | consultation detail includes `events[]` and staff-only reviews |
| floor | `GET|POST /skus` · `PATCH /skus/{id}` · `GET|POST /shade_map` · `PATCH /shade_map/{id}` | staff (writes: owner) | |
| floor | `GET /extractions?needs_review=true` · `POST /extractions/{id}/confirm` | staff | quarantined rows cannot be confirmed |
| floor | `GET /attribution` | staff | stylists see only their own row |
| floor | `GET /ledger` · `GET /ledger/verify` · `GET /price_watch` · `GET /cost` · `GET /snapshot` | staff | |
| floor | `GET /onboarding/{salon_id}` · `POST /onboarding/{salon_id}/review-docs` | staff / owner | `docs_reviewed` gates the platform agreement |
| floor | `POST /envelopes/{id}/review` | staff | draft → human_reviewed |
| agent | `POST /events` | agent | `{events:[{id, consultation_id, type, payload, ts, actor, payload_hash?}]}` → `{audit:[...]}` |
| agent | `POST /consultations` | agent | `{client_id, chair, stylist}` → `{id, ...}`; appends `state.changed` |
| agent | `PATCH /consultations/{id}/state` | agent | `{state, failing_step?, consent_ready?}` |
| agent | `POST /skus` · `PUT /shade_map` · `POST /extractions` · `PATCH /onboarding` | agent | upserts |
| agent | `POST /documents` | agent | `{kind, url?, sealed_hash?, pdf_base64?, filename?, consultation_id?}` |
| agent | `POST /envelopes` | agent | draft only; appends `envelope.requested` |
| agent | `POST /orders` | agent | `{consultation_id, items, total_cents}` → `{id, ...}`; appends `order.created` |
| agent | `POST /bookings` | agent | `{consultation_id, when, service}` → `{id, ...}`; appends `booking.created` |
| commit | `POST /envelopes/{id}/send` | owner/stylist | **the gate** (below) |
| commit | `GET /envelopes/{id}/status` | any of the salon | session URL only while sent + unexpired |
| commit | `POST /envelopes/{id}/reissue-session` | owner/stylist | fresh embedded session |

## The gate: `POST /commit/envelopes/{id}/send`

Order of checks, each a `precondition` that returns HTTP 403 (`error_type = "accessdenied"`) with the contract reason in `message`:

1. `$auth.role != "agent"` → else `agent_token_rejected`
2. `$auth.role` in owner|stylist → else `role_not_allowed`
3. `envelope.state == "human_reviewed"` → else `state_not_human_reviewed`
4. consent envelopes: `consultation.consent_ready == true` → else `consent_not_ready`; platform agreement: `onboarding.docs_reviewed == true` → else `docs_not_reviewed`
5. Foxit eSign `POST /api/folders/createfolder` with `inputType: "base64"`, `createEmbeddedSigningSession: true`, `embeddedSignersEmailIds: [signer]`
6. `envelope → sent`, `audit_event(action = "envelope.sent")`, response `{session_url, expires_at, provider_id}`

Xano's error envelope is `{"code": "ERROR_CODE_ACCESS_DENIED", "message": "<reason>"}`; the Python `EsignProxy` and Floor read `message` as the contract `reason`.

### Test matrix

```bash
BASE=https://<instance>.xano.io
AGENT=$(curl -s -X POST $BASE/api:chairside-auth/login -H 'content-type: application/json' -d '{"email":"agent@chairside.local","password":"..."}' | jq -r .authToken)
CLIENT=$(curl -s -X POST $BASE/api:chairside-auth/login -H 'content-type: application/json' -d '{"email":"client@example.com","password":"..."}' | jq -r .authToken)
OWNER=$(curl -s -X POST $BASE/api:chairside-auth/login -H 'content-type: application/json' -d '{"email":"noor@example.com","password":"..."}' | jq -r .authToken)

# 1. agent token → 403 agent_token_rejected
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api:chairside-commit/envelopes/1/send -H "Authorization: Bearer $AGENT"
curl -s -X POST $BASE/api:chairside-commit/envelopes/1/send -H "Authorization: Bearer $AGENT" | jq .message   # "agent_token_rejected"

# 2. client JWT → 403 role_not_allowed
curl -s -X POST $BASE/api:chairside-commit/envelopes/1/send -H "Authorization: Bearer $CLIENT" | jq .message   # "role_not_allowed"

# 3. owner JWT, envelope still draft → 403 state_not_human_reviewed
curl -s -X POST $BASE/api:chairside-commit/envelopes/1/send -H "Authorization: Bearer $OWNER" | jq .message    # "state_not_human_reviewed"

# 4. owner reviews the envelope, consent_ready is true → 200 with session_url
curl -s -X POST $BASE/api:chairside-floor/envelopes/1/review -H "Authorization: Bearer $OWNER"
curl -s -X POST $BASE/api:chairside-commit/envelopes/1/send -H "Authorization: Bearer $OWNER" | jq '{session_url, expires_at, provider_id}'
```

In fixtures mode the Python `EsignProxy` replays cassettes for the same four outcomes, so the matrix is testable with zero credits.

## Hash chain in Xano

`function/audit/append.xs` computes `hash = sha256(json_encode({action, actor, payload_hash, prev_hash, ts}))` with the keys written in that order (object literals keep insertion order, `json_encode` emits no whitespace). XanoScript has no sorted-key canonical JSON filter, and PHP-style `json_encode` escapes non-ASCII and `/`, so:

- `payload_hash` for agent events is computed by the agent (`chairside_agent.hashing.canonical`, tested against `docs/hash-vectors.json`) and sent in the event.
- Xano-side callers (Mirror, Floor, tasks, tools) write their payload literals with keys in alphabetical order and ASCII-only values, so `json_encode` is already canonical for them.
- A unique index on `audit_event.prev_hash` turns a concurrent double-append into a hard error instead of a forked chain.

## Background tasks

| Task | Frequency | What |
|---|---|---|
| `price_refresh` | daily 02:00 UTC | SKUs with no snapshot in 7 days → SerpApi `google_shopping` → new snapshot; `price.snapshot` event when the salon price deviates > 15 % |
| `envelope_poll` | every 2 min | `sent` envelopes → `getfolder`; completed → download, `document(kind=signed)`, `envelope.signed` |
| `session_reissue` | every 5 min | `expired` envelopes → `regenerateEmbeddedSigningSession` → back to `sent` |
| `return_reminder` | daily 07:00 UTC | bookings due within 24 h → `reminded` + `booking.created{reminder:true}` |

## MCP server

`ai/mcp_server/chairside_mcp.xs` exposes `book_appointment`, `get_consultation_summary`, `price_check`, each with `auth: "user"`. Header-capable clients connect with a user JWT as the bearer token. Claude Web and ChatGPT go through `worker-oauth/` (OAuth 2.1 → the user's own Xano JWT upstream), so a booking made from a chat client lands on Floor with `source = "mcp"` and the user's identity.

## What could not be confirmed against the docs

- Foxit eSign `getfolder` / `downloadfolder` query parameter name (`folderId`) and the `regenerateEmbeddedSigningSession` request body (`folderId`, `emailIdOfSigner`) were taken from the eSign guide's endpoint list, not from a full request example. Check them on the first live run.
- `api.request` with `Content-Type: application/x-www-form-urlencoded` and an object `params` is assumed to form-encode the body for the eSign token exchange.
- `sha256` is assumed to return lowercase hex (matches Python `hexdigest()`); verify one row against `docs/hash-vectors.json` after the first push.
- `format_timestamp:"H:i:s.v"` for milliseconds follows PHP's `v`; if the instance rejects it, drop `.v` and the agent's `ts` (which is always supplied) is unaffected.
- `sort:"":"number":false` on a scalar int array in `price/median_cents.xs` follows the documented path/type/desc argument shape; confirm on first run.
- The gate matrix could not be executed here: no Xano instance or credentials were available in this session.
