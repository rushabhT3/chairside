query "envelopes/{id}/review" verb=POST {
  api_group = "floor"
  description = "A human marks an envelope as reviewed (draft -> human_reviewed). This is the state the Commit Service checks before it will call eSign."
  auth = "user"
  input {
    int id { table = "envelope" }
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.extras.role, salon_id: $auth.extras.salon_id, expected_salon_id: null }
    } as $allowed

    db.get "envelope" {
      field_name = "id"
      field_value = $input.id
    } as $envelope

    precondition ($envelope != null && $envelope.salon_id == $auth.extras.salon_id) {
      error_type = "notfound"
      error = "envelope_not_found"
    }

    precondition ($envelope.state == "draft") {
      error_type = "accessdenied"
      error = "envelope_not_in_draft"
    }

    db.edit "envelope" {
      field_name = "id"
      field_value = $envelope.id
      data = { state: "human_reviewed", reviewed_by_user_id: $auth.id, reviewed_at: now }
    } as $updated
  }
  response = { envelope_id: $updated.id, state: $updated.state }
  guid = "UqRhND5tBPmu-9vV8T9ssk0Ldbg"
}
