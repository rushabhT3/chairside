query "price_watch" verb=GET {
  api_group = "floor"
  description = "Salon price vs latest market median per SKU; alert when the deviation exceeds 15%"
  auth = "user"
  input {
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.extras.role, salon_id: $auth.extras.salon_id, expected_salon_id: null }
    } as $allowed

    function.run "snapshot/build" {
      input = { salon_id: $auth.extras.salon_id, include_reviews: false }
    } as $snapshot
  }
  response = $snapshot.price_watch
  guid = "j7uGxZO3wqkIhhbFu9daBkdF5qc"
}
