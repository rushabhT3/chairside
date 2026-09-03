query "extractions" verb=POST {
  api_group = "agent"
  description = "Record one Nutrient extraction with per-field confidence. needs_review is true when any field is under 0.85; quarantined rows carry the quarantine_policy reasons and never feed downstream steps."
  auth = "user"
  input {
    enum source { values = ["price_list", "invoice", "intake"] }
    text file filters=trim
    json fields
    bool needs_review?=false
    bool quarantined?=false
    json quarantine_reasons?
    text consultation_id?
  }
  stack {
    function.run "rbac/require_agent" {
      input = { role: $auth.role }
    } as $allowed

    db.add "extraction_task" {
      data = {
        salon_id: $auth.salon_id,
        consultation_ref: $input.consultation_id,
        source: $input.source,
        file: $input.file,
        fields: $input.fields,
        needs_review: $input.needs_review,
        status: "pending",
        quarantined: $input.quarantined,
        quarantine_reasons: $input.quarantine_reasons
      }
    } as $task
  }
  response = { extraction_id: $task.id, needs_review: $task.needs_review, quarantined: $task.quarantined }
  guid = "8uPVZhSLDJsJP4KHYN2hp-uZ5WA"
}
