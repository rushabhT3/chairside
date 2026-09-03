query "envelopes/{id}/status" verb=GET {
  api_group = "commit"
  description = "Envelope state for Floor and Mirror. Clients may read envelopes on their own consultations; the session URL is returned only while the envelope is sent and unexpired."
  auth = "user"
  input {
    int id { table = "envelope" }
  }
  stack {
    db.get "envelope" {
      field_name = "id"
      field_value = $input.id
    } as $envelope

    precondition ($envelope != null && $envelope.salon_id == $auth.extras.salon_id) {
      error_type = "notfound"
      error = "envelope_not_found"
    }

    conditional {
      if ($auth.extras.role == "client") {
        db.query "consultation" {
          where = $db.consultation.ref == $envelope.consultation_ref
          return = { type: "single" }
        } as $consultation
        precondition ($consultation != null) {
          error_type = "accessdenied"
          error = "not_your_consultation"
        }
        db.get "client" {
          field_name = "id"
          field_value = $consultation.client_id
        } as $client
        precondition ($client.user_id == $auth.id) {
          error_type = "accessdenied"
          error = "not_your_consultation"
        }
      }
    }

    var $session_url { value = null }
    conditional {
      if ($envelope.state == "sent" && $envelope.expires_at > now) {
        var.update $session_url { value = $envelope.session_url }
      }
    }

    var $sealed_hash { value = null }
    conditional {
      if ($envelope.signed_document_id != null) {
        db.get "document" {
          field_name = "id"
          field_value = $envelope.signed_document_id
        } as $signed_document
        var.update $sealed_hash { value = $signed_document.sealed_hash }
      }
    }
  }
  response = { envelope_id: $envelope.id, state: $envelope.state, session_url: $session_url, expires_at: $envelope.expires_at, sealed_hash: $sealed_hash }
  guid = "4WYvtLZXNshrH6gi8ddAvWVXDhw"
}
