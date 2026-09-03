query "extractions" verb=GET {
  api_group = "floor"
  description = "Extraction review queue. needs_review=true returns rows with any field under the 0.85 confidence threshold; quarantined rows are always listed with their reasons."
  auth = "user"
  input {
    bool needs_review?=true
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.extras.role, salon_id: $auth.extras.salon_id, expected_salon_id: null }
    } as $allowed

    db.query "extraction_task" {
      where = $db.extraction_task.salon_id == $auth.extras.salon_id && ($db.extraction_task.needs_review ==? $input.needs_review || $db.extraction_task.quarantined == true)
      sort = { id: "asc" }
      return = { type: "list" }
    } as $rows
  }
  response = $rows
  guid = "3moNkqXjNniur2U-31LwH3Ki8gU"
}
