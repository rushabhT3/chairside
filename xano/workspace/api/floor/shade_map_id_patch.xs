query "shade_map/{id}" verb=PATCH {
  api_group = "floor"
  description = "Edit hex, undertone, level or name of one shade (owner only)"
  auth = "user"
  input {
    int id { table = "shade_map" }
    text name? filters=trim
    text hex? filters=trim|lower|min:7|max:7
    enum undertone? { values = ["warm", "cool", "neutral"] }
    int level? filters=min:1|max:10
  }
  stack {
    precondition ($auth.extras.role == "owner") {
      error_type = "accessdenied"
      error = "role_not_allowed"
    }

    db.get "shade_map" {
      field_name = "id"
      field_value = $input.id
    } as $entry

    precondition ($entry != null && $entry.salon_id == $auth.extras.salon_id) {
      error_type = "notfound"
      error = "shade_not_found"
    }

    var $updates { value = {} }
    var.update $updates { value = $updates|set_ifnotnull:"name":$input.name }
    var.update $updates { value = $updates|set_ifnotnull:"hex":$input.hex }
    var.update $updates { value = $updates|set_ifnotnull:"undertone":$input.undertone }
    var.update $updates { value = $updates|set_ifnotnull:"level":$input.level }

    precondition (($updates|is_empty) == false) {
      error_type = "inputerror"
      error = "No updates provided"
    }

    db.patch "shade_map" {
      field_name = "id"
      field_value = $entry.id
      data = $updates
    } as $updated
  }
  response = $updated
  guid = "B5B7jCO_C9F5pEmTnyu-tjJvGQo"
}
