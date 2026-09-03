query "envelopes/{id}/reissue-session" verb=POST {
  api_group = "commit"
  description = "Fresh embedded signing session for an envelope whose session expired unsigned. Same role gate as send; the envelope must already have been sent."
  auth = "user"
  input {
    int id { table = "envelope" }
  }
  stack {
    precondition ($auth.role != "agent") {
      error_type = "accessdenied"
      error = "agent_token_rejected"
    }

    precondition ($auth.role == "owner" || $auth.role == "stylist") {
      error_type = "accessdenied"
      error = "role_not_allowed"
    }

    db.get "envelope" {
      field_name = "id"
      field_value = $input.id
    } as $envelope

    precondition ($envelope != null && $envelope.salon_id == $auth.salon_id) {
      error_type = "notfound"
      error = "envelope_not_found"
    }

    precondition ($envelope.state == "sent" || $envelope.state == "expired") {
      error_type = "accessdenied"
      error = "envelope_not_sent"
    }

    function.run "esign/regenerate_session" {
      input = { folder_id: $envelope.provider_id, signer_email: $envelope.signer_email }
    } as $session

    var $expires_at { value = now|transform_timestamp:"+1 hour" }

    db.edit "envelope" {
      field_name = "id"
      field_value = $envelope.id
      data = { state: "sent", session_url: $session.session_url, expires_at: $expires_at }
    } as $updated

    security.create_uuid as $event_id
    var $stamp { value = now }
    var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }

    function.run "events/append_one" {
      input = {
        event_id: $event_id,
        salon_id: $envelope.salon_id,
        consultation_ref: $envelope.consultation_ref,
        type: "envelope.sent",
        payload: { envelope_id: $envelope.id, provider_id: $envelope.provider_id, reissued: true },
        ts: $ts,
        actor: $auth.role
      }
    } as $appended
  }
  response = { session_url: $session.session_url, expires_at: $expires_at, provider_id: $envelope.provider_id }
  guid = "3OuUVbwc07oZSrqT8R0Ltm0yVg0"
}
