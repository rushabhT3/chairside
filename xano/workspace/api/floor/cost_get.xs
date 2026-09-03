query "cost" verb=GET {
  api_group = "floor"
  description = "Units per consultation, per onboarding and per weekly refresh, derived from tool.called events"
  auth = "user"
  input {
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.role, salon_id: $auth.salon_id, expected_salon_id: null }
    } as $allowed

    function.run "snapshot/build" {
      input = { salon_id: $auth.salon_id, include_reviews: false }
    } as $snapshot
  }
  response = $snapshot.cost
  guid = "MUuIY1n2R6xTSpDXdfOHblUUJws"
}
