query "extractions/{id}/confirm" verb=POST {
  api_group = "floor"
  description = "Human confirms (optionally edits) the extracted fields of one row. Quarantined rows cannot be confirmed; they are rejected or re-extracted."
  auth = "user"
  input {
    int id { table = "extraction_task" }
    json fields?
    enum status?="confirmed" { values = ["confirmed", "rejected"] }
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.role, salon_id: $auth.salon_id, expected_salon_id: null }
    } as $allowed

    db.get "extraction_task" {
      field_name = "id"
      field_value = $input.id
    } as $task

    precondition ($task != null && $task.salon_id == $auth.salon_id) {
      error_type = "notfound"
      error = "extraction_not_found"
    }

    precondition ($task.quarantined == false || $input.status == "rejected") {
      error_type = "accessdenied"
      error = "quarantined_rows_cannot_be_confirmed"
    }

    db.edit "extraction_task" {
      field_name = "id"
      field_value = $task.id
      data = {
        fields: $input.fields ?? $task.fields,
        status: $input.status,
        needs_review: false,
        confirmed_by_user_id: $auth.id,
        confirmed_at: now
      }
    } as $updated

    conditional {
      if ($input.status == "confirmed") {
        db.query "sku" {
          where = $db.sku.extraction_task_id == $task.id
          return = { type: "list" }
        } as $skus
        foreach ($skus) {
          each as $sku {
            db.edit "sku" {
              field_name = "id"
              field_value = $sku.id
              data = { confirmed: true }
            }
          }
        }
      }
    }

    security.create_uuid as $event_id
    var $stamp { value = now }
    var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }

    function.run "events/append_one" {
      input = {
        event_id: $event_id,
        salon_id: $task.salon_id,
        consultation_ref: $task.consultation_ref,
        type: "catalog.review_queued",
        payload: { extraction_id: $task.id, status: $input.status },
        ts: $ts,
        actor: $auth.role
      }
    } as $appended
  }
  response = $updated
}
