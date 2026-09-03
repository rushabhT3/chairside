tool "price_check" {
  description = "Salon price beside the latest market spread for a product in the catalog"
  instructions = "Check a product's price. Pass part of the product name or the SKU code. Returns the salon price in cents, the market min/median/max, when it was checked, and whether the salon matches the market."
  input {
    text product filters=trim { description = "Product name fragment or SKU code" }
  }
  stack {
    precondition ($auth.id != null) {
      error_type = "accessdenied"
      error = "Authentication required"
    }

    db.query "sku" {
      where = $db.sku.salon_id == $auth.salon_id && ($db.sku.code == $input.product || $db.sku.name includes $input.product)
      sort = { code: "asc" }
      return = { type: "single" }
    } as $sku

    precondition ($sku != null) {
      error_type = "notfound"
      error = "Product not in the catalog"
    }

    db.query "price_snapshot" {
      where = $db.price_snapshot.sku_id == $sku.id
      sort = { id: "desc" }
      return = { type: "single" }
    } as $snapshot

    var $delta { value = null }
    var $action { value = "hold" }
    conditional {
      if ($snapshot != null) {
        function.run "price/delta_pct" {
          input = { salon_price_cents: $sku.salon_price_cents, median_cents: $snapshot.median_cents }
        } as $computed
        var.update $delta { value = $computed }
        var.update $action { value = "match" }
        conditional {
          if ($computed > 15) {
            var.update $action { value = "bundle" }
          }
          elseif ($computed < -15) {
            var.update $action { value = "hold" }
          }
        }
      }
    }
  }
  response = {
    sku_code: $sku.code,
    name: $sku.name,
    brand: $sku.brand,
    salon_price_cents: $sku.salon_price_cents,
    market: $snapshot,
    delta_pct: $delta,
    action: $action
  }
}
