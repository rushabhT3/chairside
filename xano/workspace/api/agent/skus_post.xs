query "skus" verb=POST {
  api_group = "agent"
  description = "Upsert SKUs from the Nutrient extraction (keyed by salon + code). Rows linked to an extraction below threshold stay unconfirmed until a human confirms them on Floor."
  auth = "user"
  input {
    json skus
  }
  stack {
    function.run "rbac/require_agent" {
      input = { role: $auth.role }
    } as $allowed

    var $written { value = 0 }
    foreach ($input.skus) {
      each as $sku {
        db.query "sku" {
          where = $db.sku.salon_id == $auth.salon_id && $db.sku.code == $sku.code
          return = { type: "single" }
        } as $existing
        conditional {
          if ($existing == null) {
            db.add "sku" {
              data = {
                salon_id: $auth.salon_id,
                code: $sku.code,
                name: $sku.name,
                brand: $sku.brand,
                salon_price_cents: $sku.salon_price_cents,
                shade_code: $sku.shade_code,
                kind: $sku.kind ?? "retail",
                confirmed: $sku.confirmed ?? false,
                extraction_task_id: $sku.extraction_task_id
              }
            }
          }
          else {
            db.edit "sku" {
              field_name = "id"
              field_value = $existing.id
              data = {
                name: $sku.name,
                brand: $sku.brand,
                salon_price_cents: $sku.salon_price_cents,
                shade_code: $sku.shade_code,
                kind: $sku.kind ?? "retail",
                confirmed: $sku.confirmed ?? $existing.confirmed,
                extraction_task_id: $sku.extraction_task_id ?? $existing.extraction_task_id
              }
            }
          }
        }
        math.add $written { value = 1 }
      }
    }
  }
  response = { written: $written }
}
