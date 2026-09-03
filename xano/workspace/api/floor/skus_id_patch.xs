query "skus/{id}" verb=PATCH {
  api_group = "floor"
  description = "Edit price, name, shade code or kind of one SKU (owner only)"
  auth = "user"
  input {
    int id { table = "sku" }
    text name? filters=trim
    int salon_price_cents? filters=min:0
    text shade_code?
    enum kind? { values = ["retail", "backbar", "service"] }
  }
  stack {
    precondition ($auth.role == "owner") {
      error_type = "accessdenied"
      error = "role_not_allowed"
    }

    db.get "sku" {
      field_name = "id"
      field_value = $input.id
    } as $sku

    precondition ($sku != null && $sku.salon_id == $auth.salon_id) {
      error_type = "notfound"
      error = "sku_not_found"
    }

    var $updates { value = {} }
    var.update $updates { value = $updates|set_ifnotnull:"name":$input.name }
    var.update $updates { value = $updates|set_ifnotnull:"salon_price_cents":$input.salon_price_cents }
    var.update $updates { value = $updates|set_ifnotnull:"shade_code":$input.shade_code }
    var.update $updates { value = $updates|set_ifnotnull:"kind":$input.kind }

    precondition (($updates|is_empty) == false) {
      error_type = "inputerror"
      error = "No updates provided"
    }

    db.patch "sku" {
      field_name = "id"
      field_value = $sku.id
      data = $updates
    } as $updated
  }
  response = $updated
  guid = "IooLqqPR8senhixjRBSRY5zmt38"
}
