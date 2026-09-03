# Commit gate on the live Xano backend

Run on 3 Sep 2026 against instance `xqbd-rqmo-jj2a.m2.xano.io`, workspace `chairside` (ID 1), after `xano workspace push` of the tables, functions, API groups, tasks, and the `chairside-mcp` server (see `xano/README.md`).

Seed rows were written through the Metadata API: one salon (Atelier Noor), three users (owner `noor@example.com`, client `amira@example.com`, service user `agent@chairside.local` with `role = agent`), one onboarding row with `docs_reviewed = false`, and three envelopes. Each user logged in through `POST /api:chairside-auth/login`; the JWT extras carry `role` and `salon_id`.

`POST /api:chairside-commit/envelopes/{id}/send` with each token:

| Caller | Envelope | HTTP | Reason |
|---|---|---|---:|
| agent service token | any | 403 | `agent_token_rejected` |
| client JWT | any | 403 | `role_not_allowed` |
| owner JWT | platform agreement, `draft` | 403 | `state_not_human_reviewed` |
| owner JWT | platform agreement, `human_reviewed`, onboarding `docs_reviewed = false` | 403 | `docs_not_reviewed` |
| owner JWT | consent, `human_reviewed`, consultation `consent_ready = false` | 403 | `consent_not_ready` |
| no token | any | 401 | `Unauthorized - Authentication Required` |

The 200 path (owner JWT, `human_reviewed`, `consent_ready = true`) calls Foxit eSign with the `FOXIT_ESIGN_*` workspace environment variables, which exist only in the Xano dashboard. It runs once those credentials are set; the agent process cannot reach it with any token it holds.

One live-runtime deviation from the validator: JWT extras are read as `$auth.extras.role`, not `$auth.role`. The validator accepts both; the runtime returns `Unable to locate auth: role` for the latter. Every gate in the workspace uses the `extras` form.

Reproduce (replace the tokens with the output of `login`):

```bash
BASE=https://xqbd-rqmo-jj2a.m2.xano.io
curl -s -X POST $BASE/api:chairside-auth/login -H 'Content-Type: application/json' \
  -d '{"email":"agent@chairside.local","password":"<password>"}'
curl -s -X POST $BASE/api:chairside-commit/envelopes/1/send -H "Authorization: Bearer <token>"
# {"code":"ERROR_CODE_ACCESS_DENIED","message":"agent_token_rejected"}
```
