query "consultations" verb=POST {
  api_group = "agent"
  description = "Open a consultation for a client at a chair with a stylist; returns the consultation ref used in every event"
  auth = "user"
  input {
    text client_id
    int chair filters=min:1
    text stylist filters=trim
  }
  stack {
    function.run "rbac/require_agent" {
      input = { role: $auth.role }
    } as $allowed

    db.query "client" {
      where = $db.client.ref == $input.client_id && $db.client.salon_id == $auth.salon_id
      return = { type: "single" }
    } as $client

    precondition ($client != null) {
      error_type = "notfound"
      error = "client_not_found"
    }

    precondition ($client.tombstoned == false) {
      error_type = "accessdenied"
      error = "client_tombstoned"
    }

    db.query "staff" {
      where = $db.staff.salon_id == $auth.salon_id && $db.staff.name == $input.stylist
      return = { type: "single" }
    } as $stylist

    security.create_uuid as $ref

    db.add "consultation" {
      data = {
        ref: $ref,
        salon_id: $auth.salon_id,
        client_id: $client.id,
        stylist_staff_id: $stylist.id,
        chair: $input.chair,
        state: "capture",
        started_at: now
      }
    } as $consultation

    security.create_uuid as $event_id
    var $stamp { value = now }
    var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }

    function.run "events/append_one" {
      input = {
        event_id: $event_id,
        salon_id: $auth.salon_id,
        consultation_ref: $consultation.ref,
        type: "state.changed",
        payload: { chair: $input.chair, state: "capture" },
        ts: $ts,
        actor: "agent"
      }
    } as $appended
  }
  response = { id: $consultation.ref, consultation_id: $consultation.ref, client_id: $client.ref, chair: $input.chair, stylist: $input.stylist }
  guid = "kpi8O9Gytmo64JPwSbZRtV2SsBc"
}
