query "consultations/{id}/state" verb=PATCH {
  api_group = "agent"
  description = "Advance the fixed-order state machine or park the consultation in needs_attention with the failing step; consent_ready is set here once consent + intake are extracted and not quarantined"
  auth = "user"
  input {
    text id
    enum state { values = ["capture", "color_tones", "skin_hd", "hair_diagnostics", "face_attributes", "plan", "simulations", "price", "consent", "commit", "done", "needs_attention"] }
    text failing_step?
    bool consent_ready?
  }
  stack {
    function.run "rbac/require_agent" {
      input = { role: $auth.role }
    } as $allowed

    db.query "consultation" {
      where = $db.consultation.ref == $input.id && $db.consultation.salon_id == $auth.salon_id
      return = { type: "single" }
    } as $consultation

    precondition ($consultation != null) {
      error_type = "notfound"
      error = "consultation_not_found"
    }

    var $updates { value = { state: $input.state, updated_at: now } }
    var.update $updates { value = $updates|set_ifnotnull:"failing_step":$input.failing_step }
    var.update $updates { value = $updates|set_ifnotnull:"consent_ready":$input.consent_ready }

    db.patch "consultation" {
      field_name = "id"
      field_value = $consultation.id
      data = $updates
    } as $updated
  }
  response = { consultation_id: $updated.ref, state: $updated.state, failing_step: $updated.failing_step, consent_ready: $updated.consent_ready }
}
