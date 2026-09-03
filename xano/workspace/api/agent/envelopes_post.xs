query "envelopes" verb=POST {
  api_group = "agent"
  description = "Create an envelope in draft. The agent can create envelopes; only a human can review one and only the Commit Service can send it."
  auth = "user"
  input {
    int document_id { table = "document" }
    text consultation_id?
    enum kind { values = ["platform_agreement", "consent"] }
    object signer {
      schema {
        text name filters=trim
        email email filters=trim|lower
      }
    }
  }
  stack {
    function.run "rbac/require_agent" {
      input = { role: $auth.extras.role }
    } as $allowed

    db.get "document" {
      field_name = "id"
      field_value = $input.document_id
    } as $document

    precondition ($document != null && $document.salon_id == $auth.extras.salon_id) {
      error_type = "notfound"
      error = "document_not_found"
    }

    precondition ($document.pdf_base64 != null) {
      error_type = "inputerror"
      error = "document_has_no_pdf"
    }

    db.add "envelope" {
      data = {
        salon_id: $auth.extras.salon_id,
        consultation_ref: $input.consultation_id,
        document_id: $document.id,
        kind: $input.kind,
        signer_name: $input.signer.name,
        signer_email: $input.signer.email,
        state: "draft"
      }
    } as $envelope

    security.create_uuid as $event_id
    var $stamp { value = now }
    var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }

    function.run "events/append_one" {
      input = {
        event_id: $event_id,
        salon_id: $auth.extras.salon_id,
        consultation_ref: $input.consultation_id,
        type: "envelope.requested",
        payload: { document_id: $document.id, envelope_id: $envelope.id, kind: $input.kind },
        ts: $ts,
        actor: "agent"
      }
    } as $appended
  }
  response = { envelope_id: $envelope.id, state: $envelope.state }
  guid = "yUXyqUlpN2cJXCKqj6fbbikEbAc"
}
