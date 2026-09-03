query "events" verb=POST {
  api_group = "agent"
  description = "Append ConsultationEvents in order; one audit_event per event. Each event may carry payload_hash computed by the agent's canonical JSON."
  auth = "user"
  input {
    json events
  }
  stack {
    function.run "rbac/require_agent" {
      input = { role: $auth.extras.role }
    } as $allowed

    precondition ($input.events|is_array) {
      error_type = "inputerror"
      error = "events must be an array"
    }

    var $audits { value = [] }
    foreach ($input.events) {
      each as $event {
        function.run "events/append_one" {
          input = {
            event_id: $event.id,
            salon_id: $auth.extras.salon_id,
            consultation_ref: $event.consultation_id,
            type: $event.type,
            payload: $event.payload ?? {},
            ts: $event.ts,
            actor: $event.actor ?? "agent",
            payload_hash: ($event|get:"payload_hash":null)
          }
        } as $appended
        var.update $audits {
          value = $audits|push:{
            id: $appended.audit.event_id,
            prev_hash: $appended.audit.prev_hash,
            hash: $appended.audit.hash,
            actor: $appended.audit.actor,
            action: $appended.audit.action,
            payload_hash: $appended.audit.payload_hash,
            ts: $appended.audit.ts
          }
        }
      }
    }
  }
  response = { audit: $audits }
  guid = "EieoEGYa-ZMwBr-51tt735YSw5Y"
}
