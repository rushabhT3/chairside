query "ledger/verify" verb=GET {
  api_group = "floor"
  description = "Server-side chain verification (same algorithm as the browser Verify button)"
  auth = "user"
  input {
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.extras.role, salon_id: $auth.extras.salon_id, expected_salon_id: null }
    } as $allowed

    function.run "audit/verify" {
      input = {}
    } as $result
  }
  response = $result
  guid = "OSQSdDqX1nm9piKEUb2AZm5kV6o"
}
