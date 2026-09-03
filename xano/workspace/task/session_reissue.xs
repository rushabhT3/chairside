task "session_reissue" {
  description = "Every 5 minutes: envelopes whose embedded session expired while unsigned get a fresh session URL so the signer can continue without a new envelope"
  active = true
  stack {
    db.query "envelope" {
      where = $db.envelope.state == "expired" && $db.envelope.provider_id != null
      sort = { id: "asc" }
      return = { type: "list" }
    } as $envelopes

    foreach ($envelopes) {
      each as $envelope {
        try_catch {
          try {
            function.run "esign/regenerate_session" {
              input = { folder_id: $envelope.provider_id, signer_email: $envelope.signer_email }
            } as $session

            db.edit "envelope" {
              field_name = "id"
              field_value = $envelope.id
              data = { state: "sent", session_url: $session.session_url, expires_at: now|transform_timestamp:"+1 hour" }
            }
          }
          catch {
            debug.log { value = "session_reissue failed for envelope " ~ ($envelope.id|to_text) }
          }
        }
      }
    }
  }
  schedule = [{starts_on: 2026-09-01 00:00:00+0000, freq: 300}]
  tags = ["esign", "envelopes"]
  guid = "z3ttgxqtjJ35TcSJWE2c7KY4dEY"
}
