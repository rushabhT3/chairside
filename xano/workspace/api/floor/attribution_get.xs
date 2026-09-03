query "attribution" verb=GET {
  api_group = "floor"
  description = "Orders and revenue per stylist and chair. Owners see every stylist; a stylist sees only their own row."
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

    var $rows { value = $snapshot.attribution }
    conditional {
      if ($auth.role == "stylist") {
        db.query "staff" {
          where = $db.staff.user_id == $auth.id
          return = { type: "single" }
        } as $me
        var.update $rows { value = $rows|filter:$$.stylist == $me.name }
      }
    }
  }
  response = $rows
}
