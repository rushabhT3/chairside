query "consultations/{id}/accept-plan" verb=POST {
  api_group = "mirror"
  description = "One tap on Mirror accepts the plan; the stylist confirms on Floor (commit)."
  auth = "user"
  input {
    text id
  }
  stack {
    db.query "consultation" {
      where = $db.consultation.ref == $input.id
      return = { type: "single" }
    } as $consultation

    precondition ($consultation != null) {
      error_type = "notfound"
      error = "consultation_not_found"
    }

    db.get "client" {
      field_name = "id"
      field_value = $consultation.client_id
    } as $client

    precondition ($auth.extras.role != "client" || $client.user_id == $auth.id) {
      error_type = "accessdenied"
      error = "not_your_consultation"
    }

    db.query "plan" {
      where = $db.plan.consultation_ref == $input.id
      return = { type: "single" }
    } as $plan

    precondition ($plan != null) {
      error_type = "notfound"
      error = "plan_not_found"
    }

    db.edit "plan" {
      field_name = "id"
      field_value = $plan.id
      data = { accepted: true, accepted_at: now }
    } as $accepted

    security.create_uuid as $event_id
    var $stamp { value = now }
    var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }

    function.run "events/append_one" {
      input = {
        event_id: $event_id,
        salon_id: $consultation.salon_id,
        consultation_ref: $consultation.ref,
        type: "plan.accepted",
        payload: { plan_id: $plan.id, total_cents: $plan.total_cents },
        ts: $ts,
        actor: "client"
      }
    } as $appended
  }
  response = { accepted: true, plan_id: $plan.id, total_cents: $plan.total_cents }
  guid = "6QGp9ylwHE3KHSdU7qswmGuvr6M"
}
