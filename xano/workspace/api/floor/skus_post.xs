query "skus" verb=POST {
  api_group = "floor"
  description = "Add one SKU by hand (owner only)"
  auth = "user"
  input {
    text code filters=trim
    text name filters=trim
    text brand filters=trim
    int salon_price_cents filters=min:0
    text shade_code?
    enum kind?="retail" { values = ["retail", "backbar", "service"] }
  }
  stack {
    precondition ($auth.role == "owner") {
      error_type = "accessdenied"
      error = "role_not_allowed"
    }

    db.add "sku" {
      data = {
        salon_id: $auth.salon_id,
        code: $input.code,
        name: $input.name,
        brand: $input.brand,
        salon_price_cents: $input.salon_price_cents,
        shade_code: $input.shade_code,
        kind: $input.kind,
        confirmed: true
      }
    } as $sku
  }
  response = $sku
  guid = "NPPhu4I3uf8_lCbim931_BQ05fk"
}
