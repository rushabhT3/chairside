query "plans/{id}" verb=PATCH {
  api_group = "floor"
  description = "Plan editor: replace services/products and totals for one plan"
  auth = "user"
  input {
    int id { table = "plan" }
    json services?
    json products?
    int total_cents? filters=min:0
    int rebook_weeks? filters=min:1|max:52
    text prose?
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.extras.role, salon_id: $auth.extras.salon_id, expected_salon_id: null }
    } as $allowed

    db.get "plan" {
      field_name = "id"
      field_value = $input.id
    } as $plan

    precondition ($plan != null) {
      error_type = "notfound"
      error = "plan_not_found"
    }

    precondition ($plan.salon_id == $auth.extras.salon_id) {
      error_type = "accessdenied"
      error = "salon_mismatch"
    }

    conditional {
      if ($input.services != null || $input.products != null) {
        db.bulk.delete "plan_item" {
          where = $db.plan_item.plan_id == $plan.id
        } as $removed
        foreach ($input.services ?? []) {
          each as $item {
            db.add "plan_item" {
              data = { plan_id: $plan.id, kind: "service", code: $item.code, name: $item.name, price_cents: $item.price_cents, qty: $item.qty ?? 1, treatment_class: $item.treatment_class ?? "none" }
            }
          }
        }
        foreach ($input.products ?? []) {
          each as $item {
            db.add "plan_item" {
              data = { plan_id: $plan.id, kind: "product", code: $item.code, name: $item.name, price_cents: $item.price_cents, qty: $item.qty ?? 1, treatment_class: "none" }
            }
          }
        }
      }
    }

    var $updates { value = { updated_at: now } }
    var.update $updates { value = $updates|set_ifnotnull:"total_cents":$input.total_cents }
    var.update $updates { value = $updates|set_ifnotnull:"rebook_weeks":$input.rebook_weeks }
    var.update $updates { value = $updates|set_ifnotnull:"prose":$input.prose }

    db.patch "plan" {
      field_name = "id"
      field_value = $plan.id
      data = $updates
    } as $updated
  }
  response = $updated
  guid = "tvmPy9MkZu4IUgkmJUTbcIAhRdk"
}
