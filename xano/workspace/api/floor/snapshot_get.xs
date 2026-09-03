query "snapshot" verb=GET {
  api_group = "floor"
  description = "The whole Floor/Mirror data snapshot (web/src/lib/snapshot.ts). Staff get competitor reviews; anyone else gets none."
  auth = "user"
  input {
  }
  stack {
    precondition ($auth.salon_id != null) {
      error_type = "accessdenied"
      error = "no_salon"
    }

    var $is_staff { value = ($auth.role == "owner" || $auth.role == "stylist") }

    function.run "snapshot/build" {
      input = { salon_id: $auth.salon_id, include_reviews: $is_staff }
    } as $snapshot
  }
  response = $snapshot
}
