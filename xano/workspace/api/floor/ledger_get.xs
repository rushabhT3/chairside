query "ledger" verb=GET {
  api_group = "floor"
  description = "Hash-chained audit events, oldest first. Floor recomputes the chain in the browser (web/src/lib/hashchain.ts)."
  auth = "user"
  input {
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.extras.role, salon_id: $auth.extras.salon_id, expected_salon_id: null }
    } as $allowed

    db.query "audit_event" {
      sort = { id: "asc" }
      return = { type: "list" }
    } as $rows
  }
  response = $rows|map:{ id: $$.event_id, prev_hash: $$.prev_hash, hash: $$.hash, actor: $$.actor, action: $$.action, payload_hash: $$.payload_hash, ts: $$.ts }
  guid = "GrXwt7IfbBjTbxwQntJC2klUdSM"
}
