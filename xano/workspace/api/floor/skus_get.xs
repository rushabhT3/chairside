query "skus" verb=GET {
  api_group = "floor"
  description = "Catalog for the caller's salon"
  auth = "user"
  input {
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.role, salon_id: $auth.salon_id, expected_salon_id: null }
    } as $allowed

    db.query "sku" {
      where = $db.sku.salon_id == $auth.salon_id
      sort = { code: "asc" }
      return = { type: "list" }
    } as $skus
  }
  response = $skus
  guid = "67cKLYvxna6FhdnYzQmDnLtBI04"
}
