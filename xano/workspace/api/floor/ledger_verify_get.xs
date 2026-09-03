query "ledger/verify" verb=GET {
  api_group = "floor"
  description = "Server-side chain verification (same algorithm as the browser Verify button)"
  auth = "user"
  input {
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.role, salon_id: $auth.salon_id, expected_salon_id: null }
    } as $allowed

    function.run "audit/verify" {
      input = {}
    } as $result
  }
  response = $result
  guid = "OSQSdDqX1nm9piKEUb2AZm5kV6o"
}
