query "envelopes/{id}/send" verb=POST {
  api_group = "commit"
  description = """
    Commit Service (brief section 8.3).
    1. role must be owner or stylist: the client role and the agent service token are rejected.
    2. envelope.state must be human_reviewed.
    3. consent envelopes need consultation.consent_ready; platform agreements need onboarding.docs_reviewed.
    4. Foxit eSign is called with the Xano-only FOXIT_ESIGN_* env vars and an embedded signing session.
    5. audit_event(action="envelope.sent") is appended.
    Every failure returns 403 with the contract reason in the error message.
  """
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

    precondition ($envelope.state == "human_reviewed") {
      error_type = "accessdenied"
      error = "state_not_human_reviewed"
    }

    conditional {
      if ($envelope.kind == "consent") {
        db.query "consultation" {
          where = $db.consultation.ref == $envelope.consultation_ref
          return = { type: "single" }
        } as $consultation
        precondition ($consultation != null && $consultation.consent_ready == true) {
          error_type = "accessdenied"
          error = "consent_not_ready"
        }
      }
      else {
        db.query "onboarding" {
          where = $db.onboarding.salon_id == $envelope.salon_id
          return = { type: "single" }
        } as $onboarding
        precondition ($onboarding != null && $onboarding.docs_reviewed == true) {
          error_type = "accessdenied"
          error = "docs_not_reviewed"
        }
      }
    }

    db.get "document" {
      field_name = "id"
      field_value = $envelope.document_id
    } as $document

    precondition ($document != null && $document.pdf_base64 != null) {
      error_type = "accessdenied"
      error = "document_has_no_pdf"
    }

    var $name_parts { value = $envelope.signer_name|split:" " }
    var $first_name { value = $name_parts|first }
    var $last_name { value = $name_parts|last }
    conditional {
      if (($name_parts|count) < 2) {
        var.update $last_name { value = "." }
      }
    }

    function.run "esign/create_folder" {
      input = {
        folder_name: "Chairside " ~ $envelope.kind ~ " #" ~ ($envelope.id|to_text),
        pdf_base64: $document.pdf_base64,
        file_name: $document.filename ?? ($envelope.kind ~ ".pdf"),
        signer_first_name: $first_name,
        signer_last_name: $last_name,
        signer_email: $envelope.signer_email
      }
    } as $folder

    var $expires_at { value = now|transform_timestamp:"+1 hour" }

    db.edit "envelope" {
      field_name = "id"
      field_value = $envelope.id
      data = {
        state: "sent",
        provider_id: $folder.folder_id,
        session_url: $folder.session_url,
        expires_at: $expires_at,
        sent_at: now
      }
    } as $sent

    security.create_uuid as $event_id
    var $stamp { value = now }
    var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }

    function.run "events/append_one" {
      input = {
        event_id: $event_id,
        salon_id: $envelope.salon_id,
        consultation_ref: $envelope.consultation_ref,
        type: "envelope.sent",
        payload: { envelope_id: $envelope.id, kind: $envelope.kind, provider_id: $folder.folder_id, signer_email: $envelope.signer_email },
        ts: $ts,
        actor: $auth.role
      }
    } as $appended
  }
  response = { session_url: $folder.session_url, expires_at: $expires_at, provider_id: $folder.folder_id }
}
