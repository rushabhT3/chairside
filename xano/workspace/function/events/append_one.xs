function "events/append_one" {
  description = "Persist one ConsultationEvent (docs/contracts.md section 2) and its audit_event row. payload_hash comes from the agent's canonical JSON; Xano stores it verbatim."
  input {
    text event_id
    int salon_id { table = "salon" }
    text consultation_ref?
    text type
    json payload?
    text ts
    text actor?="agent"
    text payload_hash?
  }
  stack {
    db.add "consultation_event" {
      data = {
        event_id: $input.event_id,
        salon_id: $input.salon_id,
        consultation_ref: $input.consultation_ref,
        type: $input.type,
        payload: $input.payload ?? {},
        ts: $input.ts,
        actor: $input.actor
      }
    } as $event_row

    function.run "audit/append" {
      input = {
        event_id: $input.event_id,
        actor: $input.actor,
        action: $input.type,
        payload: $input.payload ?? {},
        payload_hash: $input.payload_hash,
        ts: $input.ts
      }
    } as $audit_row

    conditional {
      if ($input.type == "state.changed" && $input.consultation_ref != null) {
        db.query "consultation" {
          where = $db.consultation.ref == $input.consultation_ref
          return = { type: "single" }
        } as $consultation
        conditional {
          if ($consultation != null) {
            db.edit "consultation" {
              field_name = "id"
              field_value = $consultation.id
              data = { state: $input.payload.state, updated_at: now }
            }
          }
        }
      }
    }
  }
  response = { event: $event_row, audit: $audit_row }
}
