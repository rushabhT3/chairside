query "chairs" verb=GET {
  api_group = "floor"
  description = "Today's chairs and consultation states for the caller's salon"
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
  response = $snapshot.chairs
  guid = "lx9D2qXAQHUesOF9_EXTyffZLgI"
}
