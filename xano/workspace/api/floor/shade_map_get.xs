query "shade_map" verb=GET {
  api_group = "floor"
  description = "The salon's editable shade table (hex, undertone, level per code)"
  auth = "user"
  input {
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.extras.role, salon_id: $auth.extras.salon_id, expected_salon_id: null }
    } as $allowed

    db.query "shade_map" {
      where = $db.shade_map.salon_id == $auth.extras.salon_id
      sort = { code: "asc" }
      return = { type: "list" }
    } as $entries
  }
  response = $entries
  guid = "GFtp-0AESenp5IqH4GokBavDPlA"
}
